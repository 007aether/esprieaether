(() => {
  const dialog = document.getElementById("music-dialog"), list = document.getElementById("music-queue");
  const status = document.getElementById("music-status");
  let player, selected, apiPromise;
  let currentState = "";
  const STATE_DARIJA = Object.freeze({
    "cancelled": "ملغى", "failed": "فشل", "paused": "موقوف",
    "playing": "كيشغّل", "ended": "خلص", "ready": "جاهز",
  });
  function darija(value) {
    let out = String(value ?? "");
    for (const [key, translation] of Object.entries(STATE_DARIJA)) {
      out = out.replace(new RegExp(`\\b${key}\\b`, "g"), translation);
    }
    return out;
  }
  const requestedTrack = new URLSearchParams(location.search).get("music");
  let openingRequestedTrack = false, openedRequestedTrack = false;
  async function api(path, options={}) {
    const response = await fetch(path, {...options,headers:{"Content-Type":"application/json"}});
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "طلب الموسيقى فشل");
    return body;
  }
  function youtubeApi() {
    if (window.YT?.Player) return Promise.resolve();
    if (!apiPromise) apiPromise = new Promise((resolve,reject) => {
      const timeout = setTimeout(()=>reject(new Error("مشغّل يوتيوب ما تحمّلش. تحقق من الاتصال.")),15000);
      window.onYouTubeIframeAPIReady = () => { clearTimeout(timeout); resolve(); };
      const script = document.createElement("script"); script.src="https://www.youtube.com/iframe_api";
      script.onerror=()=>{clearTimeout(timeout);reject(new Error("مشغّل يوتيوب غير متاح"));}; document.head.append(script);
    });
    return apiPromise;
  }
  async function receipt(state,error="") {
    if (!selected) return;
    try { await api(`/api/music/${selected.id}/receipt`,{method:"POST",body:JSON.stringify({state,error})}); }
    catch (err) { status.textContent=`ما تزامنتش حالة التشغيل: ${darija(err.message)}`; }
  }
  async function play(track) {
    if (!/^[A-Za-z0-9_-]{11}$/.test(track.video_id)) return;
    try {
      if (selected && selected.id !== track.id) { player?.pauseVideo(); await receipt("paused"); }
      selected=track; currentState=""; status.textContent="كيتحمّل المشغّل…";
      await youtubeApi();
      if (player) { player.loadVideoById(track.video_id); return; }
      player = new YT.Player("music-player",{height:"270",width:"100%",videoId:track.video_id,
        playerVars:{playsinline:1,origin:location.origin},events:{
          onReady:event=>{status.textContent="اضغط Play فالفيديو باش تسمع.";currentState="ready";receipt("ready");event.target.playVideo();},
          onAutoplayBlocked:()=>{status.textContent="المتصفح كيتطلب ضغطة: اضغط Play فالفيديو.";},
          onStateChange:event=>{
            // A callback for a track that is no longer selected must not report on the new one.
            if (!selected || event.target.getVideoData()?.video_id !== selected.video_id) return;
            const states={1:"playing",2:"paused",0:"ended"};
            if (states[event.data]) {currentState=states[event.data];status.textContent=`المشغّل: ${darija(states[event.data])}. الصوت كيعتمد على مستوى صوت جوالك.`;receipt(states[event.data]);}
          },
          onError:event=>{if(!selected)return;currentState="failed";const error=`خطأ تشغيل يوتيوب ${event.data}. هاد الفيديو كيقدر يمنع العرض داخل الصفحة ولا ما كاينش.`;status.textContent=error;receipt("failed",error);}
        }});
    } catch (error) {status.textContent=darija(error.message);await receipt("failed",error.message);}
  }
  async function refresh() {
    try {
      const data=await api("/api/music"); list.replaceChildren();
      if (!data.tracks.length) list.textContent="ما كاينشي موسيقى فالطابور. الصق رابط فيديو يوتيوب لتحت ولا اطلب من أتوليا تزيد واحدة.";
      for (const track of data.tracks) {
        const row=document.createElement("div"),label=document.createElement("span"),button=document.createElement("button");
        label.textContent=`${track.title} · ${darija(track.state)}`;button.textContent="شغّل هنا";button.addEventListener("click",()=>play(track));
        const remove=document.createElement("button");remove.textContent="احذف";
        remove.addEventListener("click",async()=>{
          try {if(selected?.id===track.id){selected=null;currentState="";player?.stopVideo();}await api(`/api/music/${track.id}/receipt`,{method:"POST",body:JSON.stringify({state:"cancelled"})});await refresh();}
          catch(error){status.textContent=darija(error.message);}
        });
        if(track.state!=="cancelled") {row.append(label,button,remove);list.append(row);}
      }
    } catch(error){status.textContent=darija(error.message);}
  }
  document.getElementById("quick-music")?.addEventListener("click",()=>{dialog.showModal();refresh();});
  document.getElementById("close-music").addEventListener("click",()=>dialog.close());
  document.getElementById("music-search-form")?.addEventListener("submit", async event => {
    event.preventDefault();
    const button = event.currentTarget.querySelector("button");
    const results = document.getElementById("music-search-results");
    button.disabled = true; status.textContent = "كيبحث على الموسيقى…"; results.replaceChildren();
    try {
      const data = await api("/api/music/search", {method:"POST",body:JSON.stringify({query:document.getElementById("music-search").value})});
      status.textContent = data.tracks.length ? "اختر أغنية باش تشغّلها على هاد الجهاز." : "ما لقيناش أغاني. جرّب اسماً آخر ولا رابط فيديو.";
      for (const track of data.tracks) {
        const row = document.createElement("div"), label = document.createElement("span"), start = document.createElement("button");
        label.textContent = `${track.title} · ${track.artist}`; start.textContent = "شغّل هنا";
        start.addEventListener("click", async () => {
          start.disabled = true;
          try { const added = await api("/api/music", {method:"POST",body:JSON.stringify({url:track.url,title:track.title})}); await play(added); await refresh(); }
          catch(error) { status.textContent = error.message; } finally { start.disabled = false; }
        }); row.append(label,start); results.append(row);
      }
    } catch(error) { status.textContent = error.message; } finally { button.disabled = false; }
  });
  dialog.addEventListener("close",()=>{player?.pauseVideo();});
  document.getElementById("music-form").addEventListener("submit",async event=>{
    event.preventDefault();const input=document.getElementById("music-url");
    try {await api("/api/music",{method:"POST",body:JSON.stringify({url:input.value})});input.value="";await refresh();}
    catch(error){status.textContent=darija(error.message);}
  });
  setInterval(()=>{if(dialog.open&&!document.hidden)refresh();},5000);
  // Keep the server's view of playback fresh; a stale "playing" state must not outlive the track.
  setInterval(()=>{if(selected&&currentState==="playing"&&player?.getPlayerState()===1)receipt("playing");},15000);
  async function openRequestedTrack() {
    if (!requestedTrack || openedRequestedTrack || openingRequestedTrack || document.body.classList.contains("auth-required")) return;
    openingRequestedTrack = true;
    try {
      const data = await api("/api/music");
      const track = data.tracks.find(item => item.id === requestedTrack && item.state !== "cancelled");
      if (track) {
        openedRequestedTrack = true; dialog.showModal(); await refresh();
        status.textContent = `جاهز: ${track.title}. اضغط «شغّل هنا» باش تبدا على هاد الجهاز.`;
      }
    } catch (_) { /* Sign-in can still be loading; retry after auth state changes. */ }
    finally { openingRequestedTrack = false; }
  }
  new MutationObserver(openRequestedTrack).observe(document.body, {attributes:true,attributeFilter:["class"]});
  openRequestedTrack();
})();
