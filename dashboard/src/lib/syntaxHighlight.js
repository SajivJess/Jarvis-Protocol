export function syntaxHighlight(source) {
  if (!source) return '';
  return source
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/(\/\/.*)/g, '<span class="cmt">$1</span>')
    .replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="cmt">$1</span>')
    .replace(/('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`)/g, '<span class="str">$1</span>')
    .replace(/\b(\d+\.?\d*)\b/g, '<span class="num">$1</span>')
    .replace(/\b(const|let|var|function|return|if|else|require|module|exports|true|false|null|undefined|new|typeof|try|catch|throw)\b/g, '<span class="kw">$1</span>')
    .replace(/(\w+)(\s*\()/g, '<span class="fn">$1</span>$2')
    .replace(/(===|!==|=&gt;|&amp;&amp;|\|\||[!=<>]=?)/g, '<span class="op">$1</span>');
}
