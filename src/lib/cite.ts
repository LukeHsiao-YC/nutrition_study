// 從論文 frontmatter 產生 BibTeX / RIS 引用
// 供匯出端點與詳情頁「複製引用」使用

type Data = {
  title?: string;
  authors?: string[];
  journal?: string;
  pubDate?: string;
  doi?: string;
  pmid?: string;
  link?: string;
};

function year(pubDate?: string): string {
  if (!pubDate) return '';
  const m = String(pubDate).match(/\d{4}/);
  return m ? m[0] : '';
}

// 產生引用鍵:第一作者姓 + 年份,退回 pmid,再退回 title 首字
export function citeKey(d: Data): string {
  const y = year(d.pubDate) || 'n.d.';
  if (d.authors && d.authors.length) {
    const last = d.authors[0].trim().split(/\s+/).pop() || '';
    const clean = last.replace(/[^A-Za-z0-9]/g, '');
    if (clean) return `${clean}${y}`;
  }
  if (d.pmid) return `pmid${d.pmid}`;
  const w = (d.title || 'ref').replace(/[^A-Za-z0-9]+/g, '').slice(0, 10);
  return `${w}${y}`;
}

// BibTeX 大括號值:平衡處理,避免破壞語法
function bx(v?: string): string {
  return `{${(v || '').replace(/[{}]/g, '')}}`;
}

export function toBibTeX(d: Data): string {
  const lines: string[] = [];
  const push = (k: string, v?: string) => {
    if (v && String(v).trim()) lines.push(`  ${k} = ${bx(String(v))},`);
  };
  push('title', d.title);
  if (d.authors && d.authors.length) {
    lines.push(`  author = {${d.authors.join(' and ')}},`);
  }
  push('journal', d.journal);
  const y = year(d.pubDate);
  if (y) lines.push(`  year = {${y}},`);
  push('doi', d.doi);
  if (d.pmid) lines.push(`  note = {PMID: ${d.pmid}},`);
  push('url', d.link);
  // 去掉最後一行逗號
  if (lines.length) lines[lines.length - 1] = lines[lines.length - 1].replace(/,$/, '');
  return `@article{${citeKey(d)},\n${lines.join('\n')}\n}\n`;
}

export function toRIS(d: Data): string {
  const out: string[] = ['TY  - JOUR'];
  (d.authors || []).forEach((a) => out.push(`AU  - ${a}`));
  if (d.title) out.push(`TI  - ${d.title}`);
  if (d.journal) out.push(`JO  - ${d.journal}`);
  const y = year(d.pubDate);
  if (y) out.push(`PY  - ${y}`);
  if (d.doi) out.push(`DO  - ${d.doi}`);
  if (d.pmid) out.push(`AN  - ${d.pmid}`);
  if (d.link) out.push(`UR  - ${d.link}`);
  out.push('ER  - ');
  return out.join('\n') + '\n';
}
