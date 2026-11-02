/*
 * CardioIA, Fase 3: conversor dos relatorios em Markdown para DOCX (docx-js).
 *
 * Uso: node scripts/md_para_docx.js <entrada.md> <saida.docx> "<texto do cabecalho>" [espaco entre linhas, padrao 300]
 *
 * Suporta o subconjunto de Markdown usado nos rascunhos: titulo (#), secoes
 * (## e ###), paragrafos, tabelas com cabecalho, blocos de codigo (```),
 * imagens ![legenda](caminho) seguidas de um paragrafo de legenda
 * ("Figura N. ..."), paragrafos "Tabela N. ..." antes de tabelas e a secao
 * "Referencias" com recuo deslocado. Inline: `codigo` e **negrito**.
 * Pagina A4, margens de 2,5 cm, fonte Arial 11, legendas em italico 9.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, ImageRun, Header, Footer, PageNumber, TabStopType, LevelFormat,
} = require("docx");

const [, , entrada, saida, textoCabecalho, espacoLinhaArg] = process.argv;
const ESPACO_LINHA = parseInt(espacoLinhaArg || "300", 10); // 300 = 1,25 linha; 276 = 1,15
if (!entrada || !saida) {
  console.error("uso: node md_para_docx.js <entrada.md> <saida.docx> [cabecalho]");
  process.exit(1);
}
const baseDir = path.dirname(path.resolve(entrada));
const linhas = fs.readFileSync(entrada, "utf8").split(/\r?\n/);

const FONTE = "Arial";
const FONTE_MONO = "Consolas";
const LARGURA_TEXTO_DXA = 11906 - 2 * 1418; // A4 menos margens de 2,5 cm = 9070 DXA
const LARGURA_IMAGEM_MAX_PX = 600; // ~16 cm a 96 dpi (docx-js usa pixels)

// ---------------------------------------------------------------------------
// Dimensoes de imagens (PNG e JPEG) sem dependencias externas
// ---------------------------------------------------------------------------
function dimensoes(buf, ext) {
  if (ext === "png") {
    return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  }
  // JPEG: procura o marcador SOFn
  let i = 2;
  while (i < buf.length) {
    if (buf[i] !== 0xff) { i++; continue; }
    const marcador = buf[i + 1];
    if (marcador >= 0xc0 && marcador <= 0xcf && marcador !== 0xc4 && marcador !== 0xc8 && marcador !== 0xcc) {
      return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) };
    }
    const tam = buf.readUInt16BE(i + 2);
    i += 2 + tam;
  }
  return { w: 1200, h: 800 };
}

// ---------------------------------------------------------------------------
// Inline: `codigo` e **negrito**
// ---------------------------------------------------------------------------
function runs(texto, base = {}) {
  const partes = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let ult = 0, m;
  while ((m = re.exec(texto)) !== null) {
    if (m.index > ult) partes.push(new TextRun({ text: texto.slice(ult, m.index), font: FONTE, ...base }));
    const tok = m[0];
    if (tok.startsWith("`")) partes.push(new TextRun({ text: tok.slice(1, -1), font: FONTE_MONO, size: (base.size || 22) - 2, ...base, font: FONTE_MONO }));
    else partes.push(new TextRun({ text: tok.slice(2, -2), font: FONTE, bold: true, ...base }));
    ult = m.index + tok.length;
  }
  if (ult < texto.length) partes.push(new TextRun({ text: texto.slice(ult), font: FONTE, ...base }));
  return partes;
}

function paragrafo(texto, opts = {}) {
  return new Paragraph({
    children: runs(texto, opts.run || {}),
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    spacing: { after: 120, line: ESPACO_LINHA, ...(opts.spacing || {}) },
    indent: opts.indent,
    keepNext: opts.keepNext,
  });
}

function legenda(texto) {
  return new Paragraph({
    children: [new TextRun({ text: texto, font: FONTE, italics: true, size: 18 })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 200 },
  });
}

function imagem(caminho) {
  const abs = path.resolve(baseDir, caminho);
  const buf = fs.readFileSync(abs);
  const ext = abs.toLowerCase().endsWith(".png") ? "png" : "jpg";
  const { w, h } = dimensoes(buf, ext);
  const ehLogo = /logo/i.test(abs);
  const escala = Math.min(1, (ehLogo ? 180 : LARGURA_IMAGEM_MAX_PX) / w);
  // limita tambem a altura para nao estourar a pagina (cerca de 20 cm = 756 px)
  const escalaAltura = Math.min(1, 700 / h);
  const e = Math.min(escala, escalaAltura);
  return new Paragraph({
    children: [new ImageRun({ type: ext, data: buf, transformation: { width: Math.round(w * e), height: Math.round(h * e) } })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 120 },  // "after" > 0 evita corte da imagem no LibreOffice
    keepNext: true,
  });
}

function celula(texto, larguraDxa, cabecalho = false, semBorda = false) {
  const borda = semBorda
    ? { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" }
    : { style: BorderStyle.SINGLE, size: 4, color: "808080" };
  return new TableCell({
    width: { size: larguraDxa, type: WidthType.DXA },
    borders: { top: borda, bottom: borda, left: borda, right: borda },
    shading: cabecalho ? { type: ShadingType.CLEAR, fill: "DBE8F5", color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [new Paragraph({
      children: runs(texto, { size: 18, bold: cabecalho || undefined }),
      alignment: AlignmentType.LEFT,
      spacing: { after: 0, line: 260 },
    })],
  });
}

function tabela(linhasTab, identificacao = false) {
  const parse = (l) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
  const cab = parse(linhasTab[0]);
  const corpo = linhasTab.slice(2).map(parse);
  const n = cab.length;
  // larguras: primeira coluna mais estreita quando ha 3 ou mais colunas
  let larguras;
  if (identificacao) larguras = [Math.round(LARGURA_TEXTO_DXA * 0.28), LARGURA_TEXTO_DXA - Math.round(LARGURA_TEXTO_DXA * 0.28)];
  else if (n === 2) larguras = [Math.round(LARGURA_TEXTO_DXA * 0.32), LARGURA_TEXTO_DXA - Math.round(LARGURA_TEXTO_DXA * 0.32)];
  else if (n === 3) larguras = [0.24, 0.38, 0.38].map((f) => Math.round(LARGURA_TEXTO_DXA * f));
  else if (n === 4) larguras = [0.18, 0.30, 0.17, 0.35].map((f) => Math.round(LARGURA_TEXTO_DXA * f));
  else if (n === 5) larguras = [0.19, 0.26, 0.13, 0.09, 0.33].map((f) => Math.round(LARGURA_TEXTO_DXA * f));
  else larguras = Array(n).fill(Math.round(LARGURA_TEXTO_DXA / n));
  const soma = larguras.reduce((a, b) => a + b, 0);
  larguras[larguras.length - 1] += LARGURA_TEXTO_DXA - soma;
  const rows = [];
  if (!identificacao) rows.push(new TableRow({ tableHeader: true, children: cab.map((c, i) => celula(c, larguras[i], true)) }));
  else rows.push(new TableRow({ children: cab.map((c, i) => celula(i === 0 ? `**${c}**` : c, larguras[i], false, true)) }));
  for (const r of corpo) {
    while (r.length < n) r.push("");
    rows.push(new TableRow({ children: r.map((c, i) => celula(identificacao && i === 0 ? `**${c}**` : c, larguras[i], false, identificacao)) }));
  }
  return new Table({ rows, width: { size: LARGURA_TEXTO_DXA, type: WidthType.DXA }, columnWidths: larguras });
}

function blocoCodigo(linhasCod) {
  const borda = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const pars = linhasCod.map((l) => new Paragraph({
    children: [new TextRun({ text: l.length ? l : " ", font: FONTE_MONO, size: 15 })],
    spacing: { after: 0, line: 240 },
  }));
  return new Table({
    rows: [new TableRow({ children: [new TableCell({
      width: { size: LARGURA_TEXTO_DXA, type: WidthType.DXA },
      borders: { top: borda, bottom: borda, left: borda, right: borda },
      shading: { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: pars,
    })] })],
    width: { size: LARGURA_TEXTO_DXA, type: WidthType.DXA },
    columnWidths: [LARGURA_TEXTO_DXA],
  });
}

// ---------------------------------------------------------------------------
// Varredura do Markdown
// ---------------------------------------------------------------------------
const filhos = [];
let i = 0;
let emReferencias = false;
let primeiraTabela = true;
let tituloDoc = "";
while (i < linhas.length) {
  const l = linhas[i];
  if (l.trim() === "") { i++; continue; }
  if (l.startsWith("```")) {
    const cod = [];
    i++;
    while (i < linhas.length && !linhas[i].startsWith("```")) { cod.push(linhas[i]); i++; }
    i++;
    filhos.push(blocoCodigo(cod));
    filhos.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    continue;
  }
  if (l.startsWith("# ")) {
    tituloDoc = l.slice(2).trim();
    filhos.push(new Paragraph({
      children: [new TextRun({ text: tituloDoc, font: FONTE, bold: true, size: 32, color: "1F4E79" })],
      alignment: AlignmentType.LEFT, spacing: { after: 240, line: 300 }, heading: HeadingLevel.TITLE,
    }));
    i++; continue;
  }
  if (l.startsWith("## ")) {
    const t = l.slice(3).trim();
    emReferencias = /^refer/i.test(t);
    filhos.push(new Paragraph({
      children: [new TextRun({ text: t, font: FONTE, bold: true, size: 26, color: "1F4E79" })],
      heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 140 }, keepNext: true,
    }));
    i++; continue;
  }
  if (l.startsWith("### ")) {
    filhos.push(new Paragraph({
      children: [new TextRun({ text: l.slice(4).trim(), font: FONTE, bold: true, size: 23, color: "1F4E79" })],
      heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 100 }, keepNext: true,
    }));
    i++; continue;
  }
  if (l.startsWith("|")) {
    const tab = [];
    while (i < linhas.length && linhas[i].startsWith("|")) { tab.push(linhas[i]); i++; }
    filhos.push(tabela(tab, primeiraTabela));
    primeiraTabela = false;
    filhos.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
    continue;
  }
  const img = l.match(/^!\[[^\]]*\]\(([^)]+)\)/);
  if (img) {
    filhos.push(imagem(img[1]));
    i++;
    // legenda: proximo paragrafo nao vazio comecando por "Figura"
    while (i < linhas.length && linhas[i].trim() === "") i++;
    if (i < linhas.length && /^Figura \d+\./.test(linhas[i])) { filhos.push(legenda(linhas[i].trim())); i++; }
    continue;
  }
  if (/^Tabela \d+\./.test(l)) {
    filhos.push(new Paragraph({
      children: [new TextRun({ text: l.trim(), font: FONTE, italics: true, size: 18 })],
      alignment: AlignmentType.LEFT, spacing: { before: 120, after: 80 }, keepNext: true,
    }));
    i++; continue;
  }
  // paragrafo (pode continuar em linhas seguidas)
  let texto = l.trim();
  i++;
  while (i < linhas.length && linhas[i].trim() !== "" && !/^(#|\||!\[|```)/.test(linhas[i])) { texto += " " + linhas[i].trim(); i++; }
  if (emReferencias) {
    filhos.push(new Paragraph({
      children: runs(texto, { size: 20 }), alignment: AlignmentType.LEFT,
      spacing: { after: 100, line: 260 }, indent: { left: 567, hanging: 567 },
    }));
  } else {
    filhos.push(paragrafo(texto));
  }
}

const doc = new Document({
  creator: "Silvio Prestes Guerreiro Junior",
  title: tituloDoc,
  description: "CardioIA, Fase 3, FIAP",
  styles: {
    default: { document: { run: { font: FONTE, size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", run: { font: FONTE, size: 32, bold: true, color: "1F4E79" } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONTE, size: 26, bold: true, color: "1F4E79" }, paragraph: { spacing: { before: 320, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONTE, size: 23, bold: true, color: "1F4E79" }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1418, bottom: 1418, left: 1418, right: 1418 } } },
    headers: {
      default: new Header({ children: [new Paragraph({
        children: [new TextRun({ text: textoCabecalho || "CardioIA, Fase 3", font: FONTE, size: 16, color: "666666" })],
        alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF", space: 4 } },
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        children: [
          new TextRun({ text: "Silvio Prestes Guerreiro Junior, RM 567958, 2TIAOR, Grupo 55", font: FONTE, size: 16, color: "666666" }),
          new TextRun({ text: "\tPágina ", font: FONTE, size: 16, color: "666666" }),
          new TextRun({ children: [PageNumber.CURRENT], font: FONTE, size: 16, color: "666666" }),
          new TextRun({ text: " de ", font: FONTE, size: 16, color: "666666" }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONTE, size: 16, color: "666666" }),
        ],
        tabStops: [{ type: TabStopType.RIGHT, position: LARGURA_TEXTO_DXA }],
      })] }),
    },
    children: filhos,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(saida, buf);
  console.log("gerado:", saida, buf.length, "bytes");
});
