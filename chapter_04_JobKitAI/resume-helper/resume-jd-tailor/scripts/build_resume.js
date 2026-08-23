/**
 * Config-driven resume builder.
 *   node build_resume.js config.json output.docx
 * See references/format-spec.md for the design rules this implements.
 */
const docx = require('docx');
const { Document, Packer, Paragraph, TextRun, ExternalHyperlink, AlignmentType,
        BorderStyle, TabStopType, LevelFormat, ShadingType } = docx;
const fs = require('fs');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const OUT = process.argv[3] || 'resume.docx';

const T = Object.assign({
  navy:"1F3864", dark:"222222", grey:"4A4A4A", chip:"E9EEF6", white:"FFFFFF",
  font:"Calibri", body:20, small:18, bar:17,
  marginTop:300, marginBottom:160, marginSide:846,
  lineBullet:224, spaceBullet:20, spaceChip:34, headBefore:58, headAfter:38, projBefore:70
}, cfg.theme || {});

const RIGHT_TAB = 11906 - (T.marginSide * 2);
const rule = { bottom:{ color:T.navy, space:1, style:BorderStyle.SINGLE, size:8 } };

const H = t => new Paragraph({ spacing:{before:T.headBefore, after:T.headAfter}, border:rule,
  children:[new TextRun({text:t, bold:true, size:T.body+3, color:T.navy, font:T.font, allCaps:true})] });

const bullet = kids => new Paragraph({ numbering:{reference:"b", level:0},
  spacing:{before:0, after:T.spaceBullet, line:T.lineBullet}, keepLines:true, children:kids });

const run = (text, o={}) => new TextRun(Object.assign(
  {text, size:T.body, color:T.dark, font:T.font}, o));

// summary / free paragraphs: array of {t, b?}
const richPara = (parts, sp) => new Paragraph({ spacing:sp,
  children: parts.map(p => run(p.t, p.b ? {bold:true} : {})) });

function powerBullet(b){
  const kids = [run(b.verb + " ", {bold:true, color:T.navy})];
  b.parts.forEach(p => kids.push(run(p.t, p.b ? {bold:true} : {})));
  return bullet(kids);
}

function labelBullet(it){
  return bullet([ run(it.label + " — ", {bold:true, color:T.navy}), run(it.body) ]);
}

function chipRow(r){
  const kids = [run(r.label + "  ", {bold:true, size:T.small, color:T.navy})];
  r.chips.forEach(c => {
    kids.push(run("  " + c + "  ", {size:T.small,
      shading:{type:ShadingType.CLEAR, fill:T.chip, color:"auto"}}));
    kids.push(run(" ", {size:T.small}));
  });
  return new Paragraph({spacing:{before:0, after:T.spaceChip, line:T.lineBullet+22}, children:kids});
}

function projectHeader(p){
  const out = [ new Paragraph({ spacing:{before:T.projBefore, after:0}, keepNext:true,
    tabStops:[{type:TabStopType.RIGHT, position:RIGHT_TAB}],
    children:[ run(p.project, {bold:true, size:T.body+2, color:T.navy}),
               run("\t" + p.dates, {bold:true, size:T.body}) ]}) ];
  if (p.role) out.push(new Paragraph({ spacing:{before:10, after:24}, keepNext:true,
    children:[ run(p.role, {size:T.small, color:T.grey}) ]}));
  return out;
}

function eduLine(e){
  return new Paragraph({ spacing:{before:0, after:16},
    tabStops:[{type:TabStopType.RIGHT, position:RIGHT_TAB}],
    children:[ run(e.degree, {bold:true}),
               run(e.school ? " — " + e.school : "", {size:T.small, color:T.grey}),
               run("\t" + (e.dates||""), {size:T.small, color:T.grey}) ]});
}

// ---------- header ----------
const children = [
  new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:30},
    children:[run(cfg.name, {bold:true, size:T.body+24, color:T.navy})]}),
  new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:90},
    children:[run(cfg.headline, {bold:true, size:T.body+1})]}),
];

const c = cfg.contact || {};
const barKids = [];
const plain = [c.location, c.phone].filter(Boolean).join("  |  ");
if (plain) barKids.push(run(" " + plain + "  |  ", {size:T.bar, color:T.white}));
const links = [];
if (c.email)    links.push(["mailto:" + c.email, c.email]);
if (c.linkedin) links.push([c.linkedin.startsWith("http") ? c.linkedin : "https://" + c.linkedin,
                            c.linkedin.replace(/^https?:\/\/(www\.)?/, "")]);
if (c.github)   links.push([c.github.startsWith("http") ? c.github : "https://" + c.github,
                            c.github.replace(/^https?:\/\/(www\.)?/, "")]);
links.forEach(([url, label], i) => {
  if (i) barKids.push(run("  |  ", {size:T.bar, color:T.white}));
  barKids.push(new ExternalHyperlink({link:url,
    children:[run(label, {size:T.bar, color:T.white, underline:{}})]}));
});
barKids.push(run(" ", {size:T.bar, color:T.white}));
children.push(new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:0, after:0, line:300},
  shading:{type:ShadingType.CLEAR, fill:T.navy, color:"auto"}, children:barKids}));

// ---------- sections ----------
for (const s of cfg.sections) {
  children.push(H(s.title));
  if (s.type === "paragraph")  children.push(richPara(s.parts, {after:30, line:T.lineBullet+20}));
  else if (s.type === "labelled") s.items.forEach(i => children.push(labelBullet(i)));
  else if (s.type === "skills")   s.rows.forEach(r => children.push(chipRow(r)));
  else if (s.type === "projects") s.items.forEach(p => {
      projectHeader(p).forEach(x => children.push(x));
      p.bullets.forEach(b => children.push(powerBullet(b)));
  });
  else if (s.type === "education") s.items.forEach(e => children.push(eduLine(e)));
}

const doc = new Document({
  creator: cfg.name, title: cfg.name + " - Resume",
  numbering:{config:[{reference:"b", levels:[{level:0, format:LevelFormat.BULLET, text:"▪",
    alignment:AlignmentType.LEFT,
    style:{paragraph:{indent:{left:250, hanging:180}},
           run:{color:T.navy, size:T.body, font:T.font}}}]}]},
  sections:[{ properties:{page:{ size:{width:11906, height:16838},
      margin:{top:T.marginTop, bottom:T.marginBottom, left:T.marginSide, right:T.marginSide}}},
    children }],
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("wrote " + OUT); });
