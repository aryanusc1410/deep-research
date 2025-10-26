import { useState } from "react";
export default function Chat({messagesRef}:{messagesRef: any}){
  const [local, setLocal] = useState<string>("");
  function add(){ if(!local.trim()) return;
    const msg = {role:"user", content: local.trim()};
    messagesRef.current = [...(messagesRef.current||[]), msg];
    setLocal("");
  }
  return (
    <section style={{marginTop:24}}>
      <h3>Conversation (optional)</h3>
      <div>
        {(messagesRef.current||[]).map((m:any,i:number)=>(<p key={i}><strong>{m.role}:</strong> {m.content}</p>))}
      </div>
      <div style={{display:"flex", gap:8}}>
        <input value={local} onChange={e=>setLocal(e.target.value)} placeholder="Follow-up or context..."/>
        <button onClick={add}>Add to memory</button>
      </div>
      <small>We keep a rolling window to keep costs predictable.</small>
    </section>
  );
}
