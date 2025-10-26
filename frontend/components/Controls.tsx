export default function Controls({
  onRun, disabled
}:{onRun:(q:string,p:string,m:string,t:string,b:number)=>void; disabled?:boolean;}){
  return (
    <form onSubmit={(e)=>{e.preventDefault();
      const f = new FormData(e.currentTarget as HTMLFormElement);
      onRun(String(f.get("q")), String(f.get("provider")), String(f.get("model")),
            String(f.get("template")), Number(f.get("budget")));
    }}>
      <textarea name="q" placeholder="What should the agent research?" rows={5} />
      <div className="grid grid-4" style={{marginTop:10}}>
        <select name="provider" defaultValue="openai" disabled={disabled}>
          <option value="openai">OpenAI</option>
          <option value="gemini">Gemini</option>
        </select>
        <input name="model" placeholder="(optional) model id" disabled={disabled}/>
        <select name="template" defaultValue="qa_report" disabled={disabled}>
          <option value="bullet_summary">Bullet summary</option>
          <option value="two_column">Claim/Evidence table</option>
          <option value="qa_report">Q&A report</option>
        </select>
        <input name="budget" type="number" min={1} max={10} defaultValue={4} disabled={disabled}/>
      </div>
      <button style={{marginTop:10}} disabled={disabled}>{disabled ? "Running…" : "Run"}</button>
    </form>
  );
}
