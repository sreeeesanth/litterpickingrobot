"use client";
import { useEffect, useRef, useState } from "react";

export default function Home() {
  const wsRef = useRef<WebSocket|null>(null);
  const [imgSrc, setImgSrc] = useState<string|null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = (location.hostname === "localhost" || location.hostname === "127.0.0.1")
      ? "ws://127.0.0.1:8000/ws"
      : `wss://${location.host}/ws`;
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    ws.onopen = () => { setConnected(true); console.log("WS open"); };
    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        const blob = new Blob([ev.data], { type: "image/jpeg" });
        const src = URL.createObjectURL(blob);
        setImgSrc(src);
        setTimeout(() => URL.revokeObjectURL(src), 4000);
      } else {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "trigger") {
            setEvents(prev => [{type:"trigger", payload: data.payload}, ...prev].slice(0,50));
            // also try to fetch the snapshot via HTTP (it is saved to backend/snapshots)
            const fname = data.payload.file;
            // construct URL to static file; backend serves files from cwd, so use host path
            const url = `http://127.0.0.1:8000/${fname}`;
            // show fetched snapshot as thumbnail
            fetch(url).then(r => r.blob()).then(b => {
              const blobUrl = URL.createObjectURL(b);
              setEvents(prev => [{type:"snapshot", url: blobUrl, ts: data.payload.ts}, ...prev].slice(0,50));
              // revoke later
              setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
            }).catch(()=>{/* ignore fetch errors */});
          }
        } catch(e) {
          // ignore
        }
      }
    };
    ws.onclose = () => { setConnected(false); console.log("WS closed"); };
    wsRef.current = ws;
    return () => { ws.close(); };
  }, []);

  return (
    <main style={{padding:20}}>
      <h1>Litter Placement Demo</h1>
      <div style={{display:"flex", gap:20}}>
        <div style={{flex:1}}>
          <div style={{width:640, height:480, background:"#000", display:"flex", alignItems:"center", justifyContent:"center"}}>
            {imgSrc ? <img src={imgSrc} style={{maxWidth:"100%", maxHeight:"100%"}}/> : <div style={{color:"#fff"}}>Waiting for frames...</div>}
          </div>
          <div style={{marginTop:10}}>WS: {connected ? "connected" : "disconnected"}</div>
        </div>
        <div style={{width:360}}>
          <h3>Events / Snapshots</h3>
          <div style={{maxHeight:520, overflow:"auto", background:"#f6f6f6", padding:8}}>
            {events.length===0 && <div>No events yet</div>}
            {events.map((ev, i) => (
              <div key={i} style={{padding:8, borderBottom:"1px solid #ddd"}}>
                <div style={{fontSize:12,color:"#666"}}>{ev.ts ? new Date(ev.ts*1000).toLocaleString() : new Date().toLocaleString()}</div>
                {ev.type === "snapshot" && (
                  <img src={ev.url} style={{width:"100%", marginTop:6}} />
                )}
                {ev.type === "trigger" && (
                  <div>Snapshot saved: {ev.payload && ev.payload.file}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
