  function fmt(v, d){
    return Number(v).toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
  }
  function dec(el, v){
    var d = el.getAttribute('data-pj-d');
    return (d !== null && d !== '') ? +d : (Math.abs(v) > 100 ? 2 : 5);
  }
  function poner(el, txt){ if (el.textContent !== txt) el.textContent = txt; }
  function color(el, c){ if (c && el.style.color !== c) el.style.color = c; }

