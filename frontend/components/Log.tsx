export default function Log({lines}:{lines:string[]}) {
  return (
    <div style={{maxHeight: 220, overflow:"auto", fontFamily:"ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace", fontSize:13, background:"#0b1020", color:"#d9e1ff", padding:"10px 12px", borderRadius:8, border:"1px solid #233",}}>
      {lines.length === 0 ? <div style={{opacity:.7}}>Logs will appear here…</div> :
        lines.map((l,i)=><div key={i} style={{whiteSpace:"pre-wrap"}}>{l}</div>)}
    </div>
  );
}
