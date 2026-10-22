import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const base=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(base,'workbook_rows.json'),'utf8'));
const wb=Workbook.create();
const headers=['Topic ID','Topic Name','Journal','Rank','N (fractional mass)','C (weighted citations)',
 'Score','Ranking Status','Contributing Papers','Effective Sample Size','Topic Weight Coverage',
 'Title-only N','Equal Fallback N','Unresolved Journal–Years','Classification Coverage Flag','Source ID','Citing Window','Cited Window','Model','Year'];
const widths=[10,43,68,9,18,19,17,28,18,20,20,16,18,23,40,20,16,16,10,10];
const letter=n=>String.fromCharCode(65+n);
const checks=[];
await fs.mkdir(path.join(base,'previews'),{recursive:true});
for(const year of [2023,2024,2025])for(const model of ['A','B']){
 const name=`${year}_Model_${model}`;
 const sh=wb.worksheets.add(name);sh.showGridLines=false;
 const rows=data.filter(r=>r.year===year&&r.model===model);
 if(rows.length!==576)throw Error('Expected 576 ranking records');
 const values=rows.map(r=>[r.topic_id,r.topic_name,r.journal_name,r.rank,r.N,r.C,r.score,r.ranking_status,
  r.actual_topic_paper_count,r.effective_sample_size,r.journal_valid_topic_weight_coverage,
  r.N_title_only,r.N_equal_fallback,r.unresolved_journal_years_in_window,r.classification_coverage_flag,
  r.journal_id,r.citing_window,r.cited_window,r.model,r.year]);
 sh.getRange('A1:T577').values=[headers,...values];
 sh.getRange('A1:T577').format.font={name:'Arial',size:10,color:'#172B4D'};
 sh.getRange('A1:T577').format.rowHeight=30;
 sh.getRange('A1:T577').format.verticalAlignment='center';
 sh.getRange('A1:T577').format.wrapText=false;
 const table=sh.tables.add('A1:T577',true,`Rankings_${year}_${model}`);
 table.showFilterButton=true;
 sh.getRange('A1:T1').format={fill:'#17365D',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},
  horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:38};
 sh.getRange('C2:C577').format.wrapText=true;
 sh.getRange('B2:B577').format.wrapText=true;
 sh.getRange('D2:N577').format.horizontalAlignment='right';
 sh.getRange('D2:D577').format.numberFormat='0';
 sh.getRange('E2:F577').format.numberFormat='#,##0.0000';
 sh.getRange('G2:G577').format.numberFormat='0.000000';
 sh.getRange('I2:I577').format.numberFormat='#,##0';
 sh.getRange('J2:J577').format.numberFormat='0.000';
 sh.getRange('K2:K577').format.numberFormat='0.0%';
 sh.getRange('L2:M577').format.numberFormat='0.0000';
 sh.getRange('N2:N577').format.numberFormat='0';
 sh.getRange('T2:T577').format.numberFormat='0';
 sh.getRange('N2:N577').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,
  format:{fill:'#FFF2CC',font:{color:'#7F6000'}}});
 sh.getRange('H2:H577').conditionalFormats.add('containsText',{text:'Undefined',format:{font:{color:'#777777',italic:true}}});
 widths.forEach((width,i)=>{sh.getRange(`${letter(i)}1:${letter(i)}577`).format.columnWidth=width;});
 sh.freezePanes.freezeRows(1);sh.freezePanes.freezeColumns(3);
 sh.tabColor=model==='A'?'#17365D':'#416A89';
}
wb.recalculate();
for(const year of [2023,2024,2025])for(const model of ['A','B']){
 const name=`${year}_Model_${model}`;
 const check=await wb.inspect({kind:'table',range:`${name}!A1:H5`,include:'values',tableMaxRows:5,tableMaxCols:8,maxChars:1300});
 checks.push({sheet:name,inspection:check.ndjson});
 const preview=await wb.render({sheetName:name,range:'A1:H13',scale:1.2,format:'png'});
 await fs.writeFile(path.join(base,'previews',`${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',
 options:{useRegex:true,maxResults:100},summary:'Final formula-error scan',maxChars:1800});
await fs.writeFile(path.join(base,'workbook_inspection.json'),JSON.stringify({checks,errorScan:errors.ndjson},null,2));
const out=await SpreadsheetFile.exportXlsx(wb);
await out.save(path.join(base,'W10_Journal_Rankings_2023_2025.xlsx'));
console.log('Exported six sheets with 576 records each and six previews.');
