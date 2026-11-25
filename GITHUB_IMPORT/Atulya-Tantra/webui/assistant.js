(() => {
  const $ = (selector) => document.querySelector(selector);
  const canvas = $("#voice-wave");
  const ctx = canvas.getContext("2d");
  const waveform = $("#wave-control");
  const status = $("#assistant-status");
  const statusDetail = $("#assistant-detail");
  const sessionState = $("#session-state");
  const historyStatus = $("#history-status");
  const connectionDot = $("#connection-dot");
  const textChannel = $("#text-channel");
  const voiceChannel = $("#voice-channel");
  const visionChannel = $("#vision-channel");
  const waveHelp = $("#wave-help");
  const cameraPreview = $("#camera-preview");
  const cameraFeed = $("#camera-feed");
  const cameraToggle = $("#camera-toggle");
  const cameraDevice = $("#camera-device");
  const form = $("#chat-form");
  const prompt = $("#chat-prompt");
  const messagesNode = $("#chat-messages");
  const systemDashboard = $("#system-dashboard");
  const systemOverview = $("#system-overview");
  const layoutToast = $("#layout-toast");
  const layoutFocusExit = $("#layout-focus-exit");
  const layoutVoiceToggle = $("#layout-voice-toggle");
  const layoutChatToggle = $("#layout-chat-toggle");
  const talkModeButton = $("#talk-mode");
  const cameraBus = "BroadcastChannel" in window ? new BroadcastChannel("atulya-camera") : null;
  const pageId = crypto.randomUUID?.() || `camera_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const conversation = [];
  let conversationId = getConversationId();
  const historyDialog = $("#history-dialog");
  const historyList = $("#history-list");
  const pluginDialog = $("#plugin-dialog");
  const pluginList = $("#plugin-list");
  const authDialog = $("#auth-dialog");
  const authMessage = $("#auth-message");
  const authActivate = $("#auth-activate");
  const authJoin = $("#auth-join");
  const addPasskeyButton = $("#add-passkey");
  const manageUsersButton = $("#manage-users");
  const authSetupTokenWrap = $("#auth-setup-token-wrap");
  const authSetupToken = $("#auth-setup-token");
  const authInviteWrap = $("#auth-invite-wrap");
  const authInviteToken = $("#auth-invite-token");
  const signOutButton = $("#sign-out");
  const usersDialog = $("#users-dialog");
  const usersList = $("#users-list");
  const inviteUserForm = $("#invite-user-form");
  const inviteDisplayName = $("#invite-display-name");
  const inviteResult = $("#invite-result");
  let authSetupRequired = false;
  let applicationStarted = false;
  let selectedArchiveId = conversationId;
  let historyWrites = Promise.resolve();
  let historyReady = false;
  let healthLoaded = false;
  let sceneReady = false;
  let greeted = false;
  let listening = false;
  let voiceSessionActive = false;
  let speechDetected = false;
  let lastSpeechAt = 0;
  let noiseFloor = 0.003;
  let speaking = false;
  let microphoneStream;
  let cameraStream;
  let cameraStartPromise;
  let gestureRecognizer;
  let gestureFrame = 0;
  let lastGestureFrameAt = 0;
  let gestureCurrent = "";
  let gestureModelReady = false;
  let gestureAssetsReady = false;
  let gesturesEnabled = true;
  let gestureIssue = "";
  let gestureInitializationPromise;
  let gestureFrameErrors = 0;
  let gestureCommandCandidate = "";
  let gestureCommandCandidateSince = 0;
  let gestureNeutralSince = 0;
  let gestureCommandsArmed = true;
  let lastGestureCommandAt = 0;
  const gestureCommandThreshold = 0.60;
  const gestureCommandHoldMs = 420;
  const gestureCommandCooldownMs = 1800;
  const gestureReleaseMs = 350;
  let cameraFormat = "";
  let cameraFocus = "";
  let cameraDeviceLabel = "";
  let selectedCameraDeviceId = "";
  let cameraIssue = "";
  let layoutToastTimer = 0;
  let lastMeetingNotifiedId = "";

  const GESTURE_DEFINITIONS = {
    "Open_Palm": { icon: "✋", name: "Open Palm", action: "Stop Speech & Voice", desc: "Cancels active voice, speech synthesis, and audio." },
    "Thumb_Up": { icon: "👍", name: "Thumbs Up", action: "Confirm / Send 'Yes'", desc: "Sends 'Yes' or approves pending prompt." },
    "Thumb_Down": { icon: "👎", name: "Thumbs Down", action: "Cancel / Send 'No'", desc: "Sends 'No' or cancels pending prompt." },
    "Victory": { icon: "✌️", name: "Victory / Peace", action: "Capture & Inspect Scene", desc: "Takes camera frame and inspects with AI." },
    "Pointing_Up": { icon: "☝️", name: "Pointing Up", action: "Wake Mic / Listen", desc: "Activates microphone for voice input." },
    "Closed_Fist": { icon: "✊", name: "Closed Fist", action: "Pause Media & Silence", desc: "Pauses YouTube music and silences audio." },
    "ILoveYou": { icon: "🤟", name: "Jarvis Salute", action: "System Health Briefing", desc: "Requests quick status and capability overview." },
  };

  function showGestureToast(icon, name, action) {
    const toast = document.getElementById("gesture-toast");
    if (!toast) return;
    toast.innerHTML = darija(`<span class="toast-glow">⚡</span> <strong>${icon} ${darija(name)}</strong> <span class="toast-sep">➜</span> <span>${darija(action)}</span>`);
    toast.hidden = false;
    toast.classList.remove("fade-out");
    toast.classList.add("active");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => { toast.hidden = true; toast.classList.remove("active", "fade-out"); }, 400);
    }, 2500);
  }

  function updateGestureHUD(categoryName, score, holdProgress) {
    const hud = document.getElementById("gesture-hud");
    const iconEl = document.getElementById("gesture-hud-icon");
    const nameEl = document.getElementById("gesture-hud-name");
    const scoreEl = document.getElementById("gesture-hud-score");
    const actionEl = document.getElementById("gesture-hud-action");
    const progressEl = document.getElementById("gesture-hud-progress");
    if (!hud) return;

    if (!categoryName || !GESTURE_DEFINITIONS[categoryName]) {
      hud.classList.remove("detected", "holding");
      if (iconEl) iconEl.textContent = darija("✋");
      if (nameEl) nameEl.textContent = darija("Scanning for hand");
      if (scoreEl) scoreEl.textContent = darija("");
      if (actionEl) actionEl.textContent = darija("Ready for hand gestures");
      if (progressEl) progressEl.style.width = "0%";
      return;
    }

    const def = GESTURE_DEFINITIONS[categoryName];
    hud.classList.add("detected");
    if (holdProgress > 0) hud.classList.add("holding");
    else hud.classList.remove("holding");

    if (iconEl) iconEl.textContent = def.icon;
    if (nameEl) nameEl.textContent = darija(def.name);
    if (scoreEl) scoreEl.textContent = darija(`· ${Math.round(score * 100)}%`);
    if (actionEl) actionEl.textContent = darija(`Action: ${def.action}`);
    if (progressEl) progressEl.style.width = `${Math.min(100, Math.max(0, holdProgress))}%`;
  }

  function showGestureResult(label) {
    const result = $("#gesture-result");
    if (result) result.textContent = darija(label);
  }
  let microphoneContext;
  let microphoneAnalyser;
  let speechAnalyser;
  let speechAudioContext;
  let activeAudio;
  let activeAudioUrl;
  let activeAudioRequest = 0;
  let animationFrame = 0;
  let recorder;
  let recorderChunks = [];
  let recordingMime = "audio/webm";
  let voiceRequest = 0;
  let voiceReady = false;
  let localTtsReady = false;
  let voiceBrowserBlocked = false;
  let phase = "idle";
  let syntheticPhase = 0;
  let brainReady = false;
  let visionReady = false;
  const voiceHistory = [];
  let speakingBubble;
  let activeUtterance;

  function setSystemTile(name, state, label) {
    const tile = document.querySelector(`[data-status-key="${name}"]`);
    if (!tile) return;
    tile.dataset.state = state;
    tile.querySelector("strong").textContent = darija(label);
    const level = Number(arguments[3]);
    if (Number.isFinite(level)) tile.style.setProperty("--level", `${Math.max(0, Math.min(100, level))}%`);
  }

  async function refreshSystemStatus() {
    try {
      const response = await fetch(`/api/status?conversation_id=${encodeURIComponent(conversationId)}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("Status unavailable");
      const data = await response.json();
      gestureAssetsReady = data.gesture?.state === "ready" || gestureModelReady;
      systemDashboard.dataset.state = "online";
      systemOverview.textContent = darija("LIVE");
      for (const key of ["service", "model", "cpu", "memory", "network", "host", "tools", "voice", "vision", "gesture", "telegram", "reminder", "calendar", "issue"]) {
        const item = data[key] || {};
        let label = item.label || "Unavailable";
        if (key === "issue" && cameraIssue) {
          item.state = "error";
          label = cameraIssue;
        }
        if (key === "service" && item.state === "ready") label = "Online";
        if (key === "telegram" && item.state === "setup" && /pair/i.test(label)) label = "Pairing needed";
        if (key === "reminder" && item.due_at) {
          const due = new Date(item.due_at);
          const time = Number.isNaN(due.getTime()) ? "" : `${due.toLocaleDateString([], { month: "short", day: "numeric" })} ${due.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · `;
          label = `${time}${label}`;
        }
        if (key === "calendar" && item.starts_at) {
          const starts = new Date(item.starts_at);
          const time = Number.isNaN(starts.getTime()) ? "" : `${starts.toLocaleDateString([], { month: "short", day: "numeric" })} ${starts.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · `;
          label = `${time}${label}`;
        }
        if (key === "gesture" && gestureModelReady) {
          item.state = cameraStream ? "live" : "ready";
          label = gestureCurrent || (cameraStream ? "Scanning for hand" : "Model ready · awaiting camera");
        }
        if (key === "gesture" && gestureIssue) { item.state = "error"; label = gestureIssue; }
        if (key === "gesture" && !gesturesEnabled) { item.state = "off"; label = "Gestures off"; }
        if (key === "vision" && cameraStream) {
          item.state = "live";
          label = `Camera live${cameraFormat ? ` · ${cameraFormat}` : " · on device"}${cameraFocus ? ` · ${cameraFocus}` : ""}${cameraDeviceLabel ? ` · ${cameraDeviceLabel}` : ""}`;
        }
        setSystemTile(key, item.state || "setup", label, item.level);
      }
      const meeting = data.calendar?.due;
      if (meeting?.id) {
        const key = `atulya.meeting.reminded.${meeting.id}`;
        let alreadyReminded = lastMeetingNotifiedId === String(meeting.id);
        try { alreadyReminded = alreadyReminded || sessionStorage.getItem(key) === "1"; } catch { /* Use the in-page fallback when storage is unavailable. */ }
        if (!alreadyReminded) {
          lastMeetingNotifiedId = String(meeting.id);
          try { sessionStorage.setItem(key, "1"); } catch { /* Continue with this page's notification. */ }
          const notice = `Meeting reminder: ${meeting.title}`;
          appendMessage("notice", notice);
          if (voiceSessionActive && !speaking) speak(notice);
        }
      }
      const speechWorks = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
      const speechState = data.speech?.state || (speechWorks ? "ready" : "setup");
      const speechLabel = data.speech?.label || (speechWorks ? "Browser voice" : "Unavailable");
      setSystemTile("speech", speechState, speechLabel);
    } catch {
      systemDashboard.dataset.state = "offline";
      systemOverview.textContent = darija("SERVICE UNREACHABLE");
      setSystemTile("service", "off", "Offline");
      setSystemTile("issue", "error", "Cannot reach Atulya service");
    }
  }

  function setChannelState(node, state) {
    if (!node) return;
    for (const name of ["state-ready", "state-live", "state-setup", "state-off", "active", "live", "busy", "setup", "unavailable"]) {
      node.classList.remove(name);
    }
    node.classList.add(`state-${state}`);
    const channelName = node.dataset.channelName || node.textContent.trim();
    const stateLabel = { ready: "ready", live: "active", setup: "setup required", off: "off" }[state] || state;
    node.setAttribute("aria-label", `${darija(channelName)} · ${darija(stateLabel)}`);
  }

  // Les libellés affichés sont en darija ; les comparaisons internes restent en anglais.
  const DARIJA_UI = Object.freeze({
    "Connecting": "كيتصل",
    "Connecting to Atulya.": "كيتصل بـ أتوليا.",
    "Ready": "جاهز",
    "Listening": "كيسمع",
    "Speaking": "كيتكلّم",
    "Thinking": "كيتفكّر",
    "Understanding": "كيفهم",
    "Working": "كيدير",
    "Cancelling": "كيلغي",
    "Layout updated": "التخطيط تبدّل",
    "Camera preview on": "معاينة الكاميرا شغالة",
    "Camera preview off": "معاينة الكاميرا موقوفة",
    "Chat unavailable": "المحادثة غير متاحة",
    "Voice unavailable": "الصوت غير متاح",
    "Reply unavailable": "الجواب غير متاح",
    "Service unavailable": "الخدمة غير متاحة",
    "Microphone unavailable": "الميكروفون غير متاح",
    "Microphone error": "خطأ فالميكروفون",
    "No voice heard": "ما سمعنى حتى شي صوت",
    "Allow microphone": "خلّي الميكروفون",
    "Voice paused": "الصوت موقوف",
    "Say “Hey Atulya”": "قول « يا أتوليا »",
    "Yes?": "نعم؟",
    "I missed that": "ما فهمتش",
    "Backup passkey added": "الـ passkey الاحتياطي تزاد",
    "Passkey not added": "الـ passkey ما تزادش",
    "Passkey retained": "الـ passkey باقي",
    "User not disabled": "المستعمل ما تعطّلش",
    "Device link not created": "الربط بالجهاز ما تصلّحش",
    "Invitation not created": "الدعوة ما تصلّحاتش",
    "Text chat is offline right now. The scene remains available.": "المحادثة النصية موقوفة دابا. المشهد باقي متاح.",
    "Text chat is ready. Voice input and speech are currently offline.": "المحادثة النصية جاهزة. الصوت والنطق موقوفين دابا.",
    "Atulya is ready for your next message.": "أتوليا جاهزة لرسالتك الجاية.",
    "Interrupted. Go ahead.": "وقّفت. كمل كيما بغيتي.",
    "This browser cannot play the reply aloud. The text reply is still here.": "المتصفح ما كيقدرش ينطق الجواب. الجواب المكتوب باقي هنا.",
    "The browser couldn't play the reply aloud. The text reply is still here.": "المتصفح ما قدرش ينطق الجواب. الجواب المكتوب باقي هنا.",
    "The browser couldn't start speech playback. The text reply is still here.": "المتصفح ما قدرش يبدا النطق. الجواب المكتوب باقي هنا.",
    "Running the approved action.": "كندير العملية اللي وافقت عليها.",
    "Cancelling the request.": "كيلغي الطلب.",
    "Working on your message.": "كخدّم على رسالتك.",
    "Atulya replied in chat.": "أتوليا جاوبت فالمحادثة.",
    "Try speaking again or type below.": "حاول تهضر مرة اخرى ولا اكتب من تحت.",
    "Turning your speech into text.": "كحوّل كلامك لنص.",
    "Waiting for the wake word. Everything stays on this device.": "كنستنى كلمة الإيقاظ. كلشي باقي فالجهاز.",
    "I'm listening.": "كيسمعك.",
    "Speech recognition failed. You can type below.": "التعرف على الصوت فشل. تقدر تكتب من تحت.",
    "Speak naturally. I'll answer when you pause.": "تكلّم كيف كتسول، وغادي نجاوبك إلا سكتّي.",
    "Speak naturally. Each turn sends after a pause; Atulya then listens again.": "تكلّم كيف كتسول؛ كل جولة كتبعت إلا سكتّي، ومن بعد أتوليا كترجع كتسمع.",
    "Allow the microphone for Atulya in Android settings, then tap the wave.": "خلّي الميكروفون لأتوليا فإعدادات أندرويد، من بعد اضغط على الموجة.",
    "The phone's speech service is not responding. Tap the wave to try again.": "خدمة النطق فالجوال ما كجاوبش. اضغط على الموجة باش تحاول مرة اخرى.",
    "Local speech input is not ready. Restart Atulya after voice setup completes.": "إدخال الصوت المحلي ماجاهزش. أعد تشغيل أتوليا من بعد ما يكمّل إعداد الصوت.",
    "This browser can't record microphone audio. You can type below.": "المتصفح ما كيقدرش يسجّل الصوت. تقدر تكتب من تحت.",
    "This browser can't measure microphone input. You can type below.": "المتصفح ما كيقدرش يقيس الصوت. تقدر تكتب من تحت.",
    "Grant microphone access once. Speech sends automatically after each pause.": "عطي الإذن للميكروفون مرة وحدة. الكلام كيبعت تلقائياً من بعد كل سكوت.",
    "Allow microphone access or type below.": "خلّي الميكروفون ولا اكتب من تحت.",
    "Atulya could not be reached. Restart the app and try again.": "ما قدرناش نتصلو بأتوليا. أعد تشغيل التطبيق وحاول مرة اخرى.",
    "Please sign in again to continue.": "سجّل الدخول مرة اخرى باش تكمل.",
    "Atulya was just updated. Reload the page once to continue.": "أتوليا تحدثت دابا. أعد تحميل الصفحة مرة وحدة باش تكمل.",
    "Chat is unavailable right now. You can still use the scene and camera preview.": "المحادثة غير متاحة دابا. تقدر تستعمل المشهد ومعاينة الكاميرا.",
    "Atulya couldn't complete that message. Please try again.": "أتوليا ما قدرتش تكمل الجواب. حاول مرة اخرى.",
    "Atulya returned an empty response.": "أتوليا رجّعات جواب فاضي.",
    "Atulya could not complete that reply.": "أتوليا ما قدرتش تكمل الجواب.",
    "This device can now use another passkey to unlock Atulya.": "الجهاز دابا يقدر يستعمل passkey اخرى باش يفتح أتوليا.",
    "Try again or use a different passkey device.": "حاول مرة اخرى ولا استعمل جهاز passkey مختلف.",
    "Keep another passkey enrolled first.": "خلي passkey اخرى مسجّلة أولاً.",
    "Check the values and try again.": "تحقق من القيم وحاول مرة اخرى.",
    "Try again.": "حاول مرة اخرى.",
    "Status unavailable": "الحالة غير متاحة",
    "Unavailable": "غير متاح",
    "Online": "متصل",
    "Pairing needed": "كيتطلب الربط",
    "Scanning for hand": "كيبحث على اليد",
    "Model ready · awaiting camera": "الموديل جاهز · كيستنى الكاميرا",
    "Gestures off": "الإيماءات موقوفة",
    "Ready for hand gestures": "جاهز للإيماءات باليد",
    "CAMERA OFF": "الكاميرا موقوفة",
    "PREPARING": "كيتجهّز",
    "LIVE": "مباشر",
    "LIVE VOICE · AUTO SEND AFTER A PAUSE": "صوت مباشر · إرسال تلقائي بعد السكوت",
    "ATULYA SPEAKING · MIC PAUSED": "أتوليا كتكلّم · الميكروفون موقوف",
    "PROCESSING · LISTENING RESUMES AUTOMATICALLY": "كيدير · كيرجع كيسمع تلقائياً",
    "MIC ACCESS NEEDED · ALLOW IN BROWSER": "كيتطلب الإذن للميكروفون · خلّيه فالمتصفح",
    "AUTO START · WAITING FOR PERMISSION": "بداية تلقائية · كيستنى الإذن",
    "Stop live voice conversation": "وقف المحادثة الصوتية المباشرة",
    "Start live voice conversation": "ابدا المحادثة الصوتية المباشرة",
    "Live voice is on. Each phrase sends after a pause. Activate here or press Escape to stop.": "الصوت المباشر شغال. كل عبارة كتبعت بعد السكوت. اضغط هنا ولا Escape باش توقف.",
    "Microphone starts automatically after browser permission. Each phrase then sends after a pause.": "الميكروفون كيبدا تلقائياً من بعد إذن المتصفح. كل عبارة كتبعت من بعد السكوت.",
    "ready": "جاهز",
    "active": "شغّال",
    "setup required": "كيتطلب الإعداد",
    "off": "موقوف",
    "Text": "نص",
    "Voice": "صوت",
    "Vision": "رؤية",
    "Gesture": "إيماءة",
    "SERVICE UNREACHABLE": "الخدمة غير قابلة للوصول",
    "Cannot reach Atulya service": "ما قدرناش نتصلو بخدمة أتوليا",
    "Atulya service unavailable": "خدمة أتوليا غير متاحة",
    "Atulya service online": "خدمة أتوليا متصلة",
    "No active issues": "ما كاينشي مشكل ناشط",
    "Camera off": "الكاميرا موقوفة",
    "Camera live": "الكاميرا مباشرة",
    "Camera unavailable": "الكاميرا غير متاحة",
    "Start camera preview": "ابدأ معاينة الكاميرا",
    "Stop camera preview": "وقف معاينة الكاميرا",
    "Camera access was denied. Allow it for this site in browser settings, then reload.": "الإذن للكاميرا مرفوض. خلّيها للموقع من إعدادات المتصفح، من بعد أعد التحميل.",
    "Model ready · camera off": "الموديل جاهز · الكاميرا موقوفة",
    "Gesture model needs setup": "موديل الإيماءات كيتطلب الإعداد",
    "Gesture processing failed repeatedly. Turn gestures off and on to retry; camera preview remains available.": "معالجة الإيماءات فشلت بزربات. اطفئها و شغّلها من جديد؛ معاينة الكاميرا باقية.",
    "Voice stopped by open palm.": "الصوت توقف بالكف المفتوح.",
    "Browser voice": "صوت المتصفح",
    "Unknown": "غير معروف",
    "Offline": "غير متصل",
    "Whisper · local": "Whisper · محلي",
    "Supertonic 3 · local": "Supertonic 3 · محلي",
    "Not configured": "غير مضبوط",
    "No upcoming meetings": "ما كاين اجتماعات جاية",
    "Delivery unavailable · Telegram Not configured": "التوصيل غير متاح · تيليجرام غير مضبوط",
    "The model stream ended unexpectedly.": "تدفق النموذج توقف فجأة.",
    "MODEL ERROR": "النموذج فيه خطأ",
    "RETRY NEEDED": "كيتطلب إعادة المحاولة",
    "Frame recognition failed": "التعرف على الإطار فشل",
    "SCANNING": "كيبحث",
    "CAMERA LIVE": "الكاميرا مباشرة",
    "CAMERA STARTING": "الكاميرا كتبدأ",
    "TRIGGERED": "تنفّذ",
    "Open Palm": "كف مفتوح",
    "Thumbs Up": "إبهام لأعلى",
    "Thumbs Down": "إبهام لأسفل",
    "Victory / Peace": "علامة النصر",
    "Pointing Up": "إشارة للأعلى",
    "Closed Fist": "قبضة مغلوبة",
    "Jarvis Salute": "تحية أتوليا",
    "Stop Speech & Voice": "وقف النطق والصوت",
    "Confirm / Send 'Yes'": "تأكيد / إرسال «نعم»",
    "Cancel / Send 'No'": "إلغاء / إرسال «لا»",
    "Capture & Inspect Scene": "التقاط وفحص المشهد",
    "Wake Mic / Listen": "إيقاظ الميكروفون / الاستماع",
    "Pause Media & Silence": "توقيف الوسائط وتسكيت الصوت",
    "System Health Briefing": "تقرير حالة النظام",
    "No saved conversations yet.": "ما كاينشي محادثات محفوظة.",
    "Saved conversation": "محادثة محفوظة",
    "NEW LOCAL CONVERSATION": "محادثة محلية جديدة",
    "SAVING CONVERSATION…": "كتحفظ المحادثة…",
    "CONVERSATION SAVED · ALL YOUR DEVICES": "المحادثة تحفظت · كل أجهزتك",
    "SYNCED · ALL YOUR DEVICES": "تزامنات · كل أجهزتك",
    "HISTORY OFFLINE · WILL SYNC": "الأرشيف غير متصل · غادي يتزامن",
    "LOCAL": "محلي",
    "APPROVAL NEEDED": "كيتطلب الموافقة",
    "Approval needed": "كيتطلب الموافقة",
    "APPROVE": "وافق",
    "DENY": "ارفض",
    "SIGN-IN REQUEST": "طلب تسجيل دخول",
    "ADD A PASSKEY?": "زيد passkey؟",
    "ADD PASSKEY": "زيد passkey",
    "SIGNED-IN DEVICES": "الأجهزة المسجّلة",
    "SIGN OUT ALL OTHER DEVICES": "افصل كل الأجهزة الأخرى",
    "SIGN OUT": "خروج",
    "CAMERA OFF · RETRY": "الكاميرا موقوفة · حاول مرة اخرى",
    "CAMERA LIVE": "الكاميرا مباشرة",
    "CAMERA NEEDS ACCESS": "الكاميرا كيتطلب الإذن",
    "CAMERA OFF": "الكاميرا موقوفة",
    "This browser cannot access a camera": "المتصفح ما كيقدرش يوصل للكاميرا",
    "This browser cannot access a camera. Try a current desktop browser.": "المتصفح ما كيقدرش يوصل للكاميرا. جرّب متصفح مكتبي محدّث.",
    "Camera access requires localhost or a secure HTTPS page.": "الوصول للكاميرا كيتطلب localhost ولا صفحة HTTPS آمنة.",
    "No camera profile could be opened.": "ما قدرناش نفتحو أي إعداد للكاميرا.",
    "No camera was found. Connect one or continue without the preview.": "ما لقيناش كاميرا. وصل وحدة ولا كمل بلا معاينة.",
    "The camera is busy or failed to start. Close other apps using it, then retry.": "الكاميرا مشغولة ولا ما بديتش. أغلق التطبيقات اللي كتستعملها وحاول مرة اخرى.",
    "The camera could not start. Check this site's camera permission and try again.": "الكاميرا ما بديتش. تحقق من إذن الكاميرا للموقع وحاول مرة اخرى.",
    "Gesture recognition active. Show open palm to stop speech, thumbs up for Yes, thumbs down for No, peace/victory to inspect scene.": "التعرف على الإيماءات شغال. اعرض كف مفتوح باش توقف النطق، إبهام لأعلى لـ «نعم»، إبهام لأسفل لـ «لا»، وعلامة النصر باش تفحص المشهد.",
    "Replies are spoken — tap to mute": "الجوابات كتنطق — اضغط باش تسكّت",
    "Muted — tap to speak replies": "مكتوم — اضغط باش ينطق الجوابات",
    "STOP VOICE": "وقف الصوت",
    "VOICE": "صوت",
    "VOICE: SERVER RECOGNIZER": "الصوت: التعرف على السيرفر",
    "VOICE: PHONE RECOGNIZER": "الصوت: التعرف على الجوال",
    "VOICE: BROWSER RECOGNIZER": "الصوت: التعرف على المتصفح",
    "Open website": "افتح الموقع",
    "Gestures: Inactive · Click to turn on": "الإيماءات: موقوفة · اضغط باش تشغّلها",
    "Gestures: Active · Click to turn off": "الإيماءات: شغالة · اضغط باش تطفئها",
    "Camera: Starting…": "الكاميرا: كتبدأ…",
    "Camera: Live · Click to turn off": "الكاميرا: مباشرة · اضغط باش توقفها",
    "Camera: Inactive · Click to turn on": "الكاميرا: موقوفة · اضغط باش تشغّلها",
    "Telegram sign-in failed.": "تسجيل الدخول عبر تيليجرام فشل.",
    "CREATE ADMIN PASSKEY": "أنشئ passkey للمدير",
    "ADD PASSKEY FOR THIS DEVICE": "زيد passkey لهاد الجهاز",
    "SIGN IN WITH PASSKEY": "سجّل الدخول بـ passkey",
    "Atulya could not check sign-in status.": "أتوليا ما قدرتش تتحقق من حالة تسجيل الدخول.",
    "Sign-in was denied or locked. Start again.": "تسجيل الدخول مرفوض ولا مقفول. ابدأ من جديد.",
    "The code expired. Start again.": "الرمز انقضى. ابدأ من جديد.",
    "Enter the code from Telegram, or approve on a signed-in device.": "أدخل الرمز من تيليجرام، ولا وافق من جهاز مسجّل الدخول.",
    "CREATE YOUR ACCOUNT": "أنشئ حسابك",
    "SIGN IN TO ATULYA": "سجّل الدخول لأتوليا",
    "Your account is ready once the owner approves it.": "حسابك جاهز من بعد ما يوافق عليه المالك.",
    "Choose how to confirm it's you.": "اختر كيفاش تؤكد أنك أنت.",
    "Sending a code…": "كيبعت الرمز…",
    "That code didn't match. Check it and try again.": "الرمز ما مطابقش. تحقق منه وحاول مرة اخرى.",
    "LISTENING… SAY YOUR PHRASE": "كيسمع… قول العبارة ديالك",
    "CHECKING…": "كيتحقق…",
    "Microphone unavailable here.": "الميكروفون غير متاح هنا.",
    "UNLOCK WITH VOICE": "فتح بالصوت",
    "Hide password": "أخفِ كلمة المرور",
    "Show password": "إظهار كلمة المرور",
    "Follow your device prompt to create the admin passkey.": "اتبع طلب جهازك باش تصنع passkey للمدير.",
    "Confirm with your device passkey.": "أكد بـ passkey ديال جهازك.",
    "Passkey sign-in failed. Try again.": "تسجيل الدخول بـ passkey فشل. حاول مرة اخرى.",
    "Follow your device prompt to create your private passkey.": "اتبع طلب جهازك باش تصنع passkey خاص بك.",
    "Invitation enrollment failed. Check the code and try again.": "تسجيل الدعوة فشل. تحقق من الرمز وحاول مرة اخرى.",
    "VIEW: WIDE": "العرض: واسع",
    "VIEW: CLOSE-UP": "العرض: تقريب",
    "Strong password ✓": "كلمة مرور قوية ✓",
    "Add another kind: uppercase, number or symbol": "زيد نوع اخر: حرف كبير، رقم ولا رمز",
    "Local accounts are unavailable.": "الحسابات المحلية غير متاحة.",
    "Close": "إغلاق",
    "COPY LINK": "انسخ الرابط",
    "COPIED": "تن نسخ",
    "SELECT LINK TO COPY": "اختر الرابط باش تنسخو",
    "COPY CODE": "انسخ الرمز",
    "SELECT CODE TO COPY": "اختر الرمز باش تنسخو",
    "SIGN-IN REQUEST": "طلب تسجيل دخول",
    "Passkey added. This device now signs in with one touch.": "الـ passkey تزاد. هاد الجهاز دابا كيدخل بلمسة وحدة.",
    "Passkey not added. Try again from the menu (PASSKEY +).": "الـ passkey ما تزادش. حاول مرة اخرى من القائمة (PASSKEY +).",
    "You already have an account. Confirm it's you to sign in.": "عندك حساب أصلاً. أكد أنك أنت باش تدخل.",
    "ADMIN": "مدير",
    "USER": "مستعمل",
    "ADMIN SETUP TOKEN": "رمز إعداد المدير",
    "Invitation pending": "الدعوة كتستنى",
    "Today": "اليوم",
    "messages": "رسائل",
    "PAIRING TOKEN": "رمز الربط",
    "Disable": "عطّل",
    "Enable": "شغّل",
    "Loading…": "كيتحمّل…",
    "Could not load your sign-ins.": "ما قدرناش نحمّلو جلسات الدخول ديالك.",
    "NOT NOW": "ماشي دابا",
    "Next time, unlock this device with your fingerprint, face or PIN instead of a password or code.": "المرة الجاية، افتح هاد الجهاز ببصمة الإصبع ولا الوجه ولا PIN بدل كلمة المرور ولا الرمز.",
    "Pairing failed": "الربط فشل",
    "fingerprint, face or PIN": "بصمة الإصبع، الوجه ولا PIN",
    "Privacy & Safety": "الخصوصية والسلامة",
    "Alerts on": "التنبيهات شغالة",
    "Age": "العمر",
    "tool calls": "استدعاءات أدوات",
    "Pairing token for": "رمز الربط لـ",
    "On the device run:": "على الجهاز نفّذ:",
    "I'll speak my replies.": "غادي ننطق الجوابات ديالي.",
    "Muted. I'll reply in text only.": "مكتوم. غادي نجاوب غير بالكتابة.",
    "Gestures: Active & Scanning · Click to turn off": "الإيماءات: شغالة وكتبحث · اضغط باش تطفئها",
    "Gestures: Standby (Waiting for camera) · Click to turn off": "الإيماءات: كتستنى (كتستنى الكاميرا) · اضغط باش تطفئها",
    "Live voice stopped.": "الصوت المباشر توقف.",
    "Remote first-time setup is locked. Configure ATULYA_ADMIN_SETUP_TOKEN on the server, then reload this page.": "الإعداد الأولي عن بُعد مقفول.اضبط ATULYA_ADMIN_SETUP_TOKEN على السيرفر، من بعد أعد تحميل الصفحة.",
    "Create the first administrator passkey to protect Atulya on this device.": "أنشئ أول passkey للمدير باش تحمي أتوليا على هاد الجهاز.",
    "Sign in with your fingerprint, face or screen lock, or with your username.": "سجّل الدخول ببصمة الإصبع، الوجه، قفل الشاشة، ولا باسم المستخدم ديالك.",
    "Account created. It becomes active as soon as it's verified.": "الحساب تإنشاء. غادي يتفعّل من بعد ما يتحقق.",
    "Sign-up failed.": "إنشاء الحساب فشل.",
    "Your Google account is waiting for the owner's approval.": "حساب Google ديالك كيتستنى موافقة المالك.",
    "Google sign-in failed. Try again or use another way.": "تسجيل الدخول بـ Google فشل. حاول مرة اخرى ولا استعمل طريقة اخرى.",
    "Google sign-in took too long. Try again.": "تسجيل الدخول بـ Google طال بزاف. حاول مرة اخرى.",
    "Could not sign out other devices.": "ما قدرناش نفصلو الأجهزة الأخرى.",
    "Sign out every other phone, computer and browser? They will need to sign in again.": "تفصل كل الجوالات والكمبيوترات والمتصفحات الأخرى؟ غادي يحتاجو يسجلو الدخول من جديد.",
    "Passkey not added. Try again from the menu (PASSKEY +).": "الـ passkey ما تزادش. حاول مرة اخرى من القائمة (PASSKEY +).",
    "fingerprint, face or screen lock": "بصمة الإصبع، الوجه ولا قفل الشاشة",
  });
  const DARIJA_KEYS = Object.keys(DARIJA_UI).sort((a, b) => b.length - a.length);

  function darija(value) {
    const text = String(value ?? "");
    if (Object.prototype.hasOwnProperty.call(DARIJA_UI, text)) return DARIJA_UI[text];
    const connected = text.match(/^Connected to (.+)\. Type or allow microphone access to start voice automatically\.$/);
    if (connected) return `تصلّمتي مع ${connected[1]}. اكتب رسالة ولا خلّي الميكروفون يبدأ تلقائياً.`;
    const provider = text.match(/^Configured model provider · (.+)$/);
    if (provider) return `مزوّد النموذج المضبوط · ${provider[1]}`;
    const tools = text.match(/^(\d+) tools ready · none used yet$/);
    if (tools) return `${tools[1]} أداة جاهزة · ما استعملت حتى واحدة`;
    const meeting = text.match(/^Meeting reminder: (.+)$/);
    if (meeting) return `تذكير اجتماع: ${darija(meeting[1])}`;
    const action = text.match(/^Action: (.+)$/);
    if (action) return `العملية: ${darija(action[1])}`;
    const cameraNumber = text.match(/^Camera (\d+)$/);
    if (cameraNumber) return `كاميرا ${cameraNumber[1]}`;
    const commands = text.match(/^Commands: (.+)$/);
    if (commands) return `الأوامر: ${darija(commands[1])}`;
    const signInFrom = text.match(/^Someone wants to sign in from (.+)\.$/);
    if (signInFrom) return `شي واحد بغى يدخل من ${signInFrom[1]}.`;
    const resend = text.match(/^You can resend in (\d+)s\.$/);
    if (resend) return `تقدر تعيد الإرسال من بعد ${resend[1]} ثانية.`;
    const approveOn = text.match(/^Approve on (.+) — or type the 6-digit code from Telegram\. Expires in 5 minutes\.$/);
    if (approveOn) return `وافق من ${approveOn[1]} — ولا أدخل الرمز من 6 أرقام من تيليجرام. كينقضي من بعد 5 دقائق.`;
    const signedIn = text.match(/^(\d+) signed in\. Sign out anything you don't recognise\.$/);
    if (signedIn) return `${signedIn[1]} مسجّلين. افصل أي واحد ما كتعرفوش.`;
    const signedOut = text.match(/^Signed out (\d+) other device\(s\)\.$/);
    if (signedOut) return `فصلت ${signedOut[1]} من الأجهزة الأخرى.`;
    const passkeyCount = text.match(/^(\d+) passkey\(s\)$/);
    if (passkeyCount) return `${passkeyCount[1]} passkey`;
    const pairMinutes = text.match(/^Open this on your phone or other computer within (\d+) minutes to add a passkey for your account:$/);
    if (pairMinutes) return `افتح هادشي من جوالك ولا كمبيوتر آخر خلال ${pairMinutes[1]} دقيقة باش تزيد passkey لحسابك:`;
    const shareCode = text.match(/^Share this one-time code with (.+) \(expires in 24 hours\):$/);
    if (shareCode) return `شارك هاد الرمز لمرة وحدة مع ${shareCode[1]} (كينقضي من بعد 24 ساعة):`;
    const tooShort = text.match(/^Too short \((\d+)\/10\)$/);
    if (tooShort) return `قصيرة بزاف (${tooShort[1]}/10)`;
    const usage = text.match(/^Today: (\d+)\/(\S+) messages · (\d+)\/(\S+) tool calls · Age: (.+) \((.+)\)( · alerts on)?$/);
    if (usage) return `اليوم: ${usage[1]}/${usage[2]} رسائل · ${usage[3]}/${usage[4]} استدعاءات أدوات · العمر: ${darija(usage[5])} (${darija(usage[6])})${usage[7] ? " · التنبيهات شغالة" : ""}`;
    let out = text.replace(/ · TRIGGERED$/, " · تنفّذ")
      .replace(/ · on device\b/g, " · على الجهاز")
      .replace(/ · focus /g, " · تركيز ")
      .replace(/ · Internet access/g, " · الوصول للإنترنت")
      .replace(/ · Local only/g, " · محلي فقط")
      .replace(/ · THIS DEVICE/g, " · هاد الجهاز")
      .replace(/ · alert sent/g, " · تم إرسال تنبيه")
      .replace(/ · WARNING: the log was altered/g, " · تحذير: السجل تبدّل")
      .replace(/ · waiting for approval/g, " · كيتستنى الموافقة")
      .replace(/ via /g, " عبر ")
      .replace(/ sign-in\b/g, " تسجيل الدخول")
      .replace(/ unknown network/g, " شبكة غير معروفة")
      .replace(/ signed in /g, " سجّل الدخول ")
      .replace(/ last used /g, " آخر استعمال ")
      .replace(/ passkey\(s\)/g, " passkey")
      .replace(/Today: /g, "اليوم: ")
      .replace(/ messages · /g, " رسائل · ");
    for (const key of DARIJA_KEYS) out = out.split(key).join(DARIJA_UI[key]);
    return out;
  }

  function setPhase(next, label, detail = "") {
    phase = next;
    status.textContent = darija(label);
    statusDetail.textContent = darija(detail);
    if (next === "listening" || next === "speaking") voiceHistory.length = 0;
    const tone = /UNAVAILABLE|ERROR|OFFLINE|FAILED|MISSED/i.test(label)
      ? "error"
      : /CONNECTING|ALLOW MICROPHONE|THINKING|UNDERSTANDING|PREPARING|SETUP/i.test(label)
        ? "busy"
        : next === "listening" || next === "speaking"
          ? "live"
          : "ready";
    if (sessionState) sessionState.dataset.tone = tone;
    if (typeof window.__HUM_SET_STATE === "function") window.__HUM_SET_STATE(next);
    else window.dispatchEvent(new CustomEvent("atulya:state", { detail: next }));
    waveform.dataset.phase = next;
    waveform.setAttribute("aria-label", darija(voiceSessionActive ? "Stop live voice conversation" : "Start live voice conversation"));
    waveform.title = darija(voiceSessionActive
      ? "Live voice is on. Each phrase sends after a pause. Activate here or press Escape to stop."
      : "Microphone starts automatically after browser permission. Each phrase then sends after a pause.");
    waveHelp.textContent = darija(listening
      ? "LIVE VOICE · AUTO SEND AFTER A PAUSE"
      : speaking ? "ATULYA SPEAKING · MIC PAUSED"
        : voiceSessionActive ? "PROCESSING · LISTENING RESUMES AUTOMATICALLY"
          : voiceBrowserBlocked ? "MIC ACCESS NEEDED · ALLOW IN BROWSER"
            : "AUTO START · WAITING FOR PERMISSION");
    if (voiceChannel) {
      const voiceBusy = /ALLOW MICROPHONE|PREPARING|UNDERSTANDING/i.test(label);
      const voiceLive = (listening && label === "Listening") || (speaking && label === "Speaking");
      const state = voiceLive ? "live" : voiceBusy && voiceReady ? "setup" : voiceReady && !voiceBrowserBlocked ? "ready" : voiceReady ? "off" : "setup";
      setChannelState(voiceChannel, state);
    }
    if (textChannel) {
      setChannelState(textChannel, brainReady ? "ready" : "setup");
    }
    if (connectionDot) {
      connectionDot.classList.toggle("offline", label === "Service unavailable");
      connectionDot.setAttribute("aria-label", darija(label === "Service unavailable" ? "Atulya service unavailable" : "Atulya service online"));
    }
    syncLayoutControls();
  }

  function resizeWave() {
    const bounds = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.floor(bounds.width * dpr));
    canvas.height = Math.max(1, Math.floor(bounds.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function syntheticLevel(position, time) {
    const bursts = [
      [0.12, 0.06, 0.34], [0.21, 0.035, 0.72], [0.29, 0.055, 0.47],
      [0.39, 0.035, 0.88], [0.47, 0.06, 0.55], [0.57, 0.045, 0.73],
      [0.68, 0.04, 0.94], [0.77, 0.06, 0.43], [0.88, 0.035, 0.67],
    ];
    let level = 0.025;
    for (const [center, spread, peak] of bursts) {
      const distance = (position - center) / spread;
      level += peak * Math.exp(-distance * distance * 1.8);
    }
    const ripple = 0.72 + Math.abs(Math.sin(position * 119 + time * 2.4)) * 0.28;
    return Math.min(1, level * ripple);
  }

  function drawWave() {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    // No early return when the wave is hidden (conversation mode): the analysis below also feeds the
    // hologram's glow and detects the end of each spoken turn. Only the drawing is skipped.
    const center = height / 2;
    const time = performance.now() / 1000;
    const analyser = listening ? microphoneAnalyser : speaking ? speechAnalyser : null;
    let levelHistory = null;
    if (analyser) {
      const samples = new Uint8Array(analyser.fftSize);
      analyser.getByteTimeDomainData(samples);
      let sumSquares = 0;
      for (const sample of samples) {
        const amplitude = (sample - 128) / 128;
        sumSquares += amplitude * amplitude;
      }
      const rms = Math.sqrt(sumSquares / samples.length);
      voiceHistory.push(Math.max(0, Math.min(1, (rms - 0.004) * 18)));
      if (voiceHistory.length > countForWidth(width)) voiceHistory.shift();
      levelHistory = voiceHistory;
      if (speaking) window.__HUM_ENERGY = 0.34 + Math.min(0.65, rms * 5);
      if (listening) {
        const now = performance.now();
        if (!speechDetected) noiseFloor = noiseFloor * 0.98 + Math.min(rms, 0.012) * 0.02;
        if (rms > Math.max(0.010, noiseFloor * 2.5)) {
          speechDetected = true;
          lastSpeechAt = now;
        } else if (speechDetected && now - lastSpeechAt >= 1100) {
          speechDetected = false;
          finishListening();
        }
      }
    }
    if (speaking && !analyser) {
      window.__HUM_ENERGY = 0.48 + Math.abs(Math.sin(time * 5.4)) * 0.38;
    } else if (!speaking) window.__HUM_ENERGY = 0;

    if (!width || !height) {
      animationFrame = requestAnimationFrame(drawWave); // keep analysing while hidden
      return;
    }
    ctx.clearRect(0, 0, width, height);
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, "#139de8");
    gradient.addColorStop(0.1, "#13caff");
    gradient.addColorStop(0.28, "#70eeff");
    gradient.addColorStop(0.38, "#70eeff");
    gradient.addColorStop(0.43, "#ffd17a");
    gradient.addColorStop(0.58, "#ffad48");
    gradient.addColorStop(0.66, "#21dcff");
    gradient.addColorStop(0.72, "#21dcff");
    gradient.addColorStop(0.78, "#ffad48");
    gradient.addColorStop(0.94, "#ffd17a");
    gradient.addColorStop(1, "#28cfff");
    const count = Math.max(32, Math.floor(width / 5));
    const barWidth = Math.max(1, width / count * 0.58);
    const maxHeight = Math.max(5, height * 0.45);

    ctx.beginPath();
    ctx.moveTo(0, center);
    ctx.lineTo(width, center);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 1;
    ctx.shadowColor = "#24dfff";
    ctx.shadowBlur = 2;
    ctx.stroke();

    const upper = [];
    const lower = [];
    for (let index = 0; index < count; index += 1) {
      const position = (index + 0.5) / count;
      const envelope = Math.pow(Math.sin(Math.PI * position), 0.42);
      let level;
      if (levelHistory) {
        const historyIndex = index - (count - levelHistory.length);
        level = historyIndex >= 0 ? levelHistory[historyIndex] : 0;
      } else if (speaking) {
        level = syntheticLevel(position, time + syntheticPhase);
      } else {
        level = 0;
      }
      const asymmetry = 0.88 + Math.abs(Math.sin(index * 1.71 + 0.9)) * 0.2;
      const barHeight = maxHeight * level * envelope * asymmetry;
      const x = position * width;
      upper.push([x, center - barHeight]);
      lower.push([x, center + barHeight]);
    }
    // Mirrored, softly filled waveform follows the supplied cyan-to-gold reference.
    ctx.beginPath();
    upper.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    for (let index = lower.length - 1; index >= 0; index -= 1) ctx.lineTo(lower[index][0], lower[index][1]);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.globalAlpha = listening || speaking ? 0.58 : 0.92;
    ctx.shadowColor = "#29dfff";
    ctx.shadowBlur = listening || speaking ? 11 : 5;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.beginPath();
    upper.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 1.4;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Bracket marks echo the supplied reference waveform.
    ctx.beginPath();
    ctx.moveTo(10, center - height * 0.32);
    ctx.quadraticCurveTo(2, center, 10, center + height * 0.32);
    ctx.moveTo(width - 10, center - height * 0.32);
    ctx.quadraticCurveTo(width - 2, center, width - 10, center + height * 0.32);
    ctx.strokeStyle = "rgba(110,210,255,.66)";
    ctx.lineWidth = 1.2;
    ctx.stroke();
    animationFrame = requestAnimationFrame(drawWave);
  }

  function countForWidth(width) {
    return Math.max(32, Math.floor(width / 5));
  }

  function refreshWave() {
    cancelAnimationFrame(animationFrame);
    animationFrame = requestAnimationFrame(drawWave);
  }

  function getConversationId() {
    const key = "atulya.conversation.id";
    try {
      let id = localStorage.getItem(key);
      if (!id) {
        id = crypto.randomUUID?.() || `c_${Date.now()}_${Math.random().toString(36).slice(2)}`;
        localStorage.setItem(key, id);
      }
      return id;
    } catch {
      return `c_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    }
  }

  function readArchiveIndex() {
    try {
      const entries = JSON.parse(localStorage.getItem("atulya.conversations.index") || "[]");
      return Array.isArray(entries) ? entries.filter((item) => item && /^[A-Za-z0-9_-]{1,80}$/.test(item.id)).slice(0, 50) : [];
    } catch { return []; }
  }

  function rememberArchive(id, title = "") {
    const entries = readArchiveIndex();
    const existing = entries.find((item) => item.id === id);
    const next = { id, title: title || existing?.title || "New conversation", updated: new Date().toISOString() };
    try { localStorage.setItem("atulya.conversations.index", JSON.stringify([next, ...entries.filter((item) => item.id !== id)].slice(0, 50))); } catch { /* The current page can continue without an archive index. */ }
  }

  // Conversations come from the server (all devices), merged with this browser's local index.
  let serverArchive = [];
  async function refreshServerArchive() {
    try {
      const response = await fetch("/api/conversations", { headers: { Accept: "application/json" }, cache: "no-store" });
      if (response.ok) serverArchive = (await response.json()).conversations || [];
    } catch { /* offline: local index only */ }
  }

  function drawArchiveList(refetch = true) {
    if (!historyList) return;
    if (refetch) refreshServerArchive().then(() => drawArchiveList(false));
    historyList.replaceChildren();
    const local = readArchiveIndex();
    const seen = new Set(serverArchive.map((item) => item.id));
    const entries = [...serverArchive, ...local.filter((item) => !seen.has(item.id))]
      .sort((a, b) => String(b.updated).localeCompare(String(a.updated)));
    if (!entries.length) {
      const empty = document.createElement("p");
      empty.className = "history-warning";
      empty.textContent = darija("No saved conversations yet.");
      historyList.append(empty);
      return;
    }
    for (const entry of entries) {
      const row = document.createElement("div");
      row.className = "history-entry";
      const choose = document.createElement("button");
      choose.type = "button";
      choose.textContent = darija(entry.title || "Saved conversation");
      choose.setAttribute("aria-current", String(entry.id === selectedArchiveId));
      choose.addEventListener("click", () => { selectedArchiveId = entry.id; drawArchiveList(false); });
      choose.addEventListener("dblclick", () => { void openArchiveConversation(); });
      const date = document.createElement("small");
      const parsed = new Date(entry.updated);
      date.textContent = darija(Number.isNaN(parsed.getTime()) ? "LOCAL" : parsed.toLocaleString([], { dateStyle: "short", timeStyle: "short" }));
      row.append(choose, date);
      historyList.append(row);
    }
  }

  function startNewConversation() {
    conversationId = crypto.randomUUID?.() || `c_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    selectedArchiveId = conversationId;
    conversation.length = 0;
    messagesNode.replaceChildren();
    try { localStorage.setItem("atulya.conversation.id", conversationId); } catch { /* Keep the generated ID for this page only. */ }
    historyReady = true;
    historyStatus.textContent = darija("NEW LOCAL CONVERSATION");
    historyStatus.dataset.state = "saved";
    rememberArchive(conversationId);
    historyDialog?.close();
    prompt?.focus();
  }

  async function openArchiveConversation() {
    if (!selectedArchiveId || selectedArchiveId === conversationId) { historyDialog?.close(); return; }
    const response = await fetch(`/api/conversations/${encodeURIComponent(selectedArchiveId)}`, { headers: { Accept: "application/json" } });
    if (!response.ok) { showLayoutToast("That saved conversation could not be opened."); return; }
    const body = await response.json();
    conversationId = selectedArchiveId;
    try { localStorage.setItem("atulya.conversation.id", conversationId); } catch { /* Continue in memory only. */ }
    conversation.length = 0;
    messagesNode.replaceChildren();
    for (const message of body.messages || []) {
      if (message.role === "notice") continue;
      appendMessage(message.role, message.content, message.message_id, false);
      conversation.push({ role: message.role, content: message.content });
    }
    historyDialog?.close();
  }

  async function exportArchive() {
    if (!selectedArchiveId) return;
    const response = await fetch(`/api/conversations/${encodeURIComponent(selectedArchiveId)}`, { headers: { Accept: "application/json" } });
    if (!response.ok) { showLayoutToast("Conversation export failed."); return; }
    const payload = await response.json();
    const blob = new Blob([JSON.stringify({ app: "Atulya", exported_at: new Date().toISOString(), conversation_id: selectedArchiveId, messages: payload.messages }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `atulya-conversation-${selectedArchiveId}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function deleteArchive() {
    if (!selectedArchiveId || !window.confirm("Permanently delete this saved conversation from the local archive?")) return;
    const response = await fetch(`/api/conversations/${encodeURIComponent(selectedArchiveId)}`, { method: "DELETE" });
    if (!response.ok) { showLayoutToast("Conversation deletion failed."); return; }
    try { localStorage.setItem("atulya.conversations.index", JSON.stringify(readArchiveIndex().filter((item) => item.id !== selectedArchiveId))); } catch { /* The server archive has still been deleted. */ }
    if (selectedArchiveId === conversationId) startNewConversation();
    else { selectedArchiveId = conversationId; drawArchiveList(); }
  }

  async function showPluginSettings() {
    if (!pluginList || !pluginDialog) return;
    pluginList.replaceChildren();
    const response = await fetch("/api/plugins", { headers: { Accept: "application/json" } });
    if (!response.ok) { showLayoutToast("Built-in tool settings are unavailable."); return; }
    const { plugins = [] } = await response.json();
    for (const plugin of plugins) {
      const row = document.createElement("label");
      row.className = "plugin-entry";
      const description = document.createElement("span");
      const title = document.createElement("strong");
      title.textContent = darija(`${plugin.category.toUpperCase()} · ${plugin.name}`);
      const detail = document.createElement("small");
      detail.textContent = darija(`Commands: ${(plugin.commands || []).join(", ")}${plugin.permissions?.includes("network") ? " · Internet access" : " · Local only"}`);
      description.append(title, detail);
      const toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.checked = Boolean(plugin.enabled);
      toggle.setAttribute("aria-label", darija(`${plugin.enabled ? "Disable" : "Enable"} ${plugin.name}`));
      toggle.addEventListener("change", async () => {
        toggle.disabled = true;
        try {
          const result = await fetch(`/api/plugins/${encodeURIComponent(plugin.id)}`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: toggle.checked }),
          });
          if (!result.ok) throw new Error("Save failed");
          const body = await result.json();
          plugin.enabled = body.plugin.enabled;
          toggle.setAttribute("aria-label", darija(`${plugin.enabled ? "Disable" : "Enable"} ${plugin.name}`));
        } catch {
          toggle.checked = !toggle.checked;
          showLayoutToast(`Could not update ${plugin.name}.`);
        } finally { toggle.disabled = false; }
      });
      row.append(description, toggle);
      pluginList.append(row);
    }
    pluginDialog.showModal();
  }

  function saveMessage(message) {
    if (!historyReady) return;
    historyStatus.textContent = darija("SAVING CONVERSATION…");
    historyWrites = historyWrites.catch(() => {}).then(async () => {
      const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: message.dataset.messageId, role: message.classList.contains("notice") ? "notice" : message.classList.contains("user") ? "user" : "assistant", content: message.textContent }),
      keepalive: true,
      });
      if (!response.ok) throw new Error("History save failed");
      historyStatus.textContent = darija("CONVERSATION SAVED · ALL YOUR DEVICES");
      historyStatus.dataset.state = "saved";
    }).catch(() => {
      historyStatus.textContent = darija("HISTORY OFFLINE · WILL SYNC");
      historyStatus.dataset.state = "error";
    });
  }

  function appendMessage(role, text, messageId = null, persist = true) {
    const item = document.createElement("p");
    item.className = `chat-message ${role}`;
    item.dataset.messageId = messageId || (crypto.randomUUID?.() || `m_${Date.now()}_${Math.random().toString(36).slice(2)}`);
    item.textContent = text;
    messagesNode.append(item);
    while (messagesNode.children.length > 60) messagesNode.firstElementChild.remove();
    messagesNode.scrollTop = messagesNode.scrollHeight;
    // Notices describe transient failures, not conversation turns. Keep them
    // visible for this page session, but don't restore stale errors next time.
    if (persist && role !== "notice") saveMessage(item);
    if (role === "user") {
      const priorUser = [...messagesNode.querySelectorAll(".chat-message.user")].find((message) => message !== item);
      rememberArchive(conversationId, (priorUser?.textContent || text).slice(0, 72));
    }
    return item;
  }


  // ---- Computer-action approvals -------------------------------------------
  // The model can only *request* PC actions; they run after the user taps
  // Approve or answers "yes" by voice/text while a request is waiting.
  const pendingActions = new Map();

  function showActionRequest(action) {
    if (!action?.id || pendingActions.has(action.id)) return;
    const card = document.createElement("div");
    card.className = "chat-message action-card";
    card.setAttribute("role", "group");
    card.setAttribute("aria-label", darija("Approval needed"));
    const title = document.createElement("strong");
    title.textContent = darija("APPROVAL NEEDED");
    const summary = document.createElement("span");
    summary.textContent = darija(action.summary);
    const buttons = document.createElement("div");
    const approve = document.createElement("button");
    approve.type = "button";
    approve.textContent = darija("APPROVE");
    approve.className = "approve";
    const deny = document.createElement("button");
    deny.type = "button";
    deny.textContent = darija("DENY");
    approve.addEventListener("click", () => decideAction(action.id, true));
    deny.addEventListener("click", () => decideAction(action.id, false));
    buttons.append(approve, deny);
    card.append(title, summary, buttons);
    messagesNode.append(card);
    messagesNode.scrollTop = messagesNode.scrollHeight;
    card.dataset.created = String(Date.now());
    pendingActions.set(action.id, card);
  }

  async function decideAction(id, approve) {
    const card = pendingActions.get(id);
    if (!card) return;
    pendingActions.delete(id);
    card.querySelectorAll("button").forEach((button) => { button.disabled = true; });
    card.dataset.state = approve ? "approved" : "denied";
    let text;
    try {
      const response = await fetch(`/api/actions/${encodeURIComponent(id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ approve }),
      });
      const body = await response.json().catch(() => ({}));
      text = response.ok ? String(body.text || "Done.") : String(body.detail || "That request could not be completed.");
    } catch {
      text = "Atulya couldn't reach the computer to do that.";
    }
    appendMessage("assistant", text);
    conversation.push({ role: "assistant", content: text });
    return text;
  }

  // "yes" / "approve" / "haan" and "no" / "cancel" answer the newest waiting request.
  function approvalAnswer(text) {
    if (!pendingActions.size) return null;
    // Spoken/typed "yes" only counts for a fresh request; older ones need a tap,
    // so a stray "yes" from a TV or another person can't approve something stale.
    const [latestCard] = [...pendingActions.values()].slice(-1);
    if (Date.now() - Number(latestCard?.dataset.created || 0) > 60000) return null;
    const value = text.toLowerCase().replace(/[.!?,]/g, " ").trim();
    if (/^(?:yes|yeah|yep|sure|ok|okay|approve|approved|do it|go ahead|haan|ha|ji haan|confirm)(?: please| it)?$/.test(value)) return true;
    if (/^(?:no|nope|deny|cancel|stop|don't|do not|nahi|na)(?: please| it)?$/.test(value)) return false;
    return null;
  }

  // ---- Live sync: changes from Telegram, the app or another screen appear here immediately ----
  let liveEvents = null;
  function startLiveSync() {
    if (liveEvents || !("EventSource" in window)) return;
    liveEvents = new EventSource("/api/events");
    liveEvents.onmessage = (message) => {
      let event = {};
      try { event = JSON.parse(message.data); } catch { return; }
      if (event.type !== "conversation") return;
      if (historyDialog?.open) drawArchiveList();
      if (event.id === conversationId && phase !== "thinking" && !speaking) reloadCurrentConversation();
    };
    liveEvents.onerror = () => { /* EventSource reconnects by itself */ };
  }

  async function reloadCurrentConversation() {
    const keep = [...messagesNode.querySelectorAll(".action-card")];
    messagesNode.replaceChildren();
    await restoreConversation();
    keep.forEach((card) => messagesNode.append(card));
  }

  // An old cached page talking to a newer server: reload once quietly instead of asking the user.
  function selfHealReload() {
    let last = 0;
    try { last = Number(sessionStorage.getItem("atulya.selfHealAt") || 0); } catch { /* ignore */ }
    if (Date.now() - last < 60000) return false;
    try { sessionStorage.setItem("atulya.selfHealAt", String(Date.now())); } catch { /* ignore */ }
    location.reload();
    return true;
  }

  async function restoreConversation() {
    try {
      const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("History could not be loaded");
      const body = await response.json();
      rememberArchive(conversationId, (body.messages || []).find((message) => message.role === "user")?.content?.slice(0, 72) || "New conversation");
      for (const message of body.messages || []) {
        if (message.role === "notice") continue;
        appendMessage(message.role, message.content, message.message_id, false);
        if (message.role === "user" || message.role === "assistant") conversation.push({ role: message.role, content: message.content });
      }
      if (conversation.length > 38) conversation.splice(0, conversation.length - 38);
      historyReady = true;
      historyStatus.textContent = darija("SYNCED · ALL YOUR DEVICES");
      historyStatus.dataset.state = "saved";
    } catch {
      historyReady = true;
      historyStatus.textContent = darija("HISTORY OFFLINE · WILL SYNC");
      historyStatus.dataset.state = "error";
    }
  }

  $("#new-conversation")?.addEventListener("click", startNewConversation);
  $("#open-history")?.addEventListener("click", () => {
    selectedArchiveId = conversationId;
    rememberArchive(conversationId);
    drawArchiveList();
    historyDialog?.showModal();
  });
  $("#close-history")?.addEventListener("click", () => historyDialog?.close());
  $("#open-history-selected")?.addEventListener("click", openArchiveConversation);
  $("#export-history")?.addEventListener("click", exportArchive);
  $("#delete-history")?.addEventListener("click", deleteArchive);
  $("#open-plugins")?.addEventListener("click", showPluginSettings);
  $("#close-plugins")?.addEventListener("click", () => pluginDialog?.close());

  function highlightSpokenReply(item) {
    if (speakingBubble) speakingBubble.classList.remove("is-speaking");
    speakingBubble = item;
    if (speakingBubble) {
      speakingBubble.classList.add("is-speaking");
      speakingBubble.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  function clearSpokenReply() {
    if (speakingBubble) speakingBubble.classList.remove("is-speaking");
    speakingBubble = undefined;
  }

  function restoreIdlePhase(detailOverride = "") {
    speaking = false;
    clearSpokenReply();
    if (!brainReady) setPhase("idle", "Chat unavailable", detailOverride || "Text chat is offline right now. The scene remains available.");
    else if (!voiceReady) setPhase("idle", "Voice unavailable", detailOverride || "Text chat is ready. Voice input and speech are currently offline.");
    else setPhase("idle", "Ready", detailOverride || "Atulya is ready for your next message.");
    refreshWave();
  }

  function stopCamera() {
    if (gestureFrame) cancelAnimationFrame(gestureFrame);
    gestureFrame = 0;
    gestureRecognizer?.close?.();
    gestureRecognizer = undefined;
    gestureModelReady = false;
    gestureCurrent = "";
    const gestureRegion = $("#gesture-region");
    if (gestureRegion) gestureRegion.dataset.state = gestureAssetsReady ? "ready" : "setup";
    showGestureResult(gestureAssetsReady ? "CAMERA OFF" : "PREPARING");
    if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = undefined;
    document.body.classList.remove("camera-on");
    if (cameraFeed) cameraFeed.srcObject = null;
    cameraPreview?.classList.remove("is-live");
    cameraToggle?.setAttribute("aria-pressed", "false");
    cameraToggle?.setAttribute("aria-label", darija("Start camera preview"));
    const label = cameraToggle?.querySelector(".preview-label b");
    if (label) label.innerHTML = darija("<i></i> CAMERA OFF · RETRY");
    if (visionChannel) setChannelState(visionChannel, "off");
    const gestureChannel = $("#gesture-channel");
    if (gestureChannel) setChannelState(gestureChannel, gestureAssetsReady ? "ready" : "setup");
    setSystemTile("vision", "off", "Camera off");
    setSystemTile("gesture", gestureAssetsReady ? "ready" : "setup", gestureAssetsReady ? "Model ready · camera off" : "Gesture model needs setup");
  }

  cameraBus?.addEventListener("message", (event) => {
    if (event.data?.type === "claim" && event.data.pageId !== pageId && cameraStream) stopCamera();
  });

  async function refreshCameraDevices(activeDeviceId = "") {
    if (!cameraDevice || !navigator.mediaDevices?.enumerateDevices) return;
    try {
      const devices = (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === "videoinput");
      const savedDeviceId = selectedCameraDeviceId || (() => {
        try { return localStorage.getItem("atulya.camera.deviceId") || ""; } catch { return ""; }
      })();
      const preferred = activeDeviceId || savedDeviceId;
      cameraDevice.replaceChildren();
      for (const [index, device] of devices.entries()) {
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent = device.label || darija(`Camera ${index + 1}`);
        cameraDevice.append(option);
      }
      cameraDevice.hidden = devices.length < 2;
      if (devices.some((device) => device.deviceId === preferred)) {
        cameraDevice.value = preferred;
        selectedCameraDeviceId = preferred;
      } else if (activeDeviceId) {
        selectedCameraDeviceId = activeDeviceId;
      }
    } catch { /* Keep the default browser-selected camera if enumeration is unavailable. */ }
  }

  async function startCamera(retry = 0) {
    if (cameraStream) {
      return true;
    }
    if (cameraStartPromise) return cameraStartPromise;
    if (!navigator.mediaDevices?.getUserMedia) {
      const detail = window.isSecureContext ? "This browser cannot access a camera. Try a current desktop browser." : "Camera access requires localhost or a secure HTTPS page.";
      setCameraError("This browser cannot access a camera", detail);
      return false;
    }
    cameraStartPromise = (async () => {
      try {
        cameraBus?.postMessage({ type: "claim", pageId });
        // Give another Atulya tab time to release the device before requesting it.
        await new Promise((resolve) => window.setTimeout(resolve, 180));
        let stream;
        let cameraError;
        const requestedDevice = selectedCameraDeviceId
          || (() => { try { return localStorage.getItem("atulya.camera.deviceId") || ""; } catch { return ""; } })();
        const deviceConstraint = requestedDevice ? { deviceId: { exact: requestedDevice } } : { facingMode: { ideal: "user" } };
        const videoProfiles = [
          { ...deviceConstraint, width: { min: 1920, ideal: 1920 }, height: { min: 1080, ideal: 1080 }, frameRate: { ideal: 30 } },
          { ...deviceConstraint, width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } },
          { ...deviceConstraint, width: { ideal: 1280 }, height: { ideal: 720 } },
          deviceConstraint,
          ...(requestedDevice ? [] : [true]),
        ];
        for (const video of videoProfiles) {
          try {
            stream = await navigator.mediaDevices.getUserMedia({ video, audio: false });
            break;
          } catch (error) {
            cameraError = error;
            if (["NotAllowedError", "PermissionDeniedError", "NotFoundError", "SecurityError"].includes(error.name)) throw error;
          }
        }
        if (!stream) throw cameraError || new Error("No camera profile could be opened.");
        cameraStream = stream;
        document.body.classList.add("camera-on");
        for (const track of stream.getVideoTracks()) {
          let capabilities = {};
          try { capabilities = track.getCapabilities?.() || {}; } catch { /* Use the camera's default controls. */ }
          const cameraControls = {};
          if (capabilities.focusMode?.includes("continuous")) cameraControls.focusMode = "continuous";
          if (capabilities.exposureMode?.includes("continuous")) cameraControls.exposureMode = "continuous";
          if (Object.keys(cameraControls).length) {
            try { await track.applyConstraints({ advanced: [cameraControls] }); } catch { /* Unsupported control: keep browser defaults. */ }
          }
        }
        cameraFeed.srcObject = stream;
        await cameraFeed.play();
        cameraPreview.classList.add("is-live");
        if (visionChannel) setChannelState(visionChannel, "live");
        if (cameraToggle) {
          cameraToggle.setAttribute("aria-pressed", "true");
          cameraToggle.setAttribute("aria-label", darija("Stop camera preview"));
          const label = cameraToggle.querySelector(".preview-label b");
          if (label) label.innerHTML = darija("<i></i> CAMERA LIVE");
        }
        stream.getVideoTracks().forEach((track) => track.addEventListener("ended", stopCamera, { once: true }));
        const cameraSettings = stream.getVideoTracks()[0]?.getSettings?.() || {};
        cameraFormat = cameraSettings.width && cameraSettings.height ? `${cameraSettings.width}×${cameraSettings.height}` : "";
        cameraFocus = cameraSettings.focusMode || "";
        selectedCameraDeviceId = cameraSettings.deviceId || selectedCameraDeviceId;
        try { if (selectedCameraDeviceId) localStorage.setItem("atulya.camera.deviceId", selectedCameraDeviceId); } catch { /* Session still works without local preferences. */ }
        await refreshCameraDevices(selectedCameraDeviceId);
        const activeDevice = (await navigator.mediaDevices.enumerateDevices().catch(() => []))
          .find((device) => device.kind === "videoinput" && device.deviceId === selectedCameraDeviceId);
        cameraDeviceLabel = activeDevice?.label || "";
        const resolvedCameraIssue = cameraIssue;
        cameraIssue = "";
        const issueLabel = document.querySelector('[data-status-key="issue"] strong');
        if (resolvedCameraIssue && issueLabel?.textContent === darija(resolvedCameraIssue)) setSystemTile("issue", "ready", "No active issues");
        const label = cameraToggle?.querySelector(".preview-label b");
        if (label) label.textContent = darija(`CAMERA LIVE${cameraFormat ? ` · ${cameraFormat}` : ""}`);
        setSystemTile("vision", "live", `Camera live${cameraFormat ? ` · ${cameraFormat}` : " · on device"}${cameraFocus ? ` · focus ${cameraFocus}` : ""}${cameraDeviceLabel ? ` · ${cameraDeviceLabel}` : ""}`);
        if (status.textContent === darija("Camera unavailable")) restoreIdlePhase();
        if (gesturesEnabled) await initializeGestureRecognition();
        return true;
      } catch (error) {
        stopCamera();
        cameraFormat = "";
        cameraFocus = "";
        const deviceBusy = error.name === "NotReadableError" || error.name === "AbortError";
        const detail = error.name === "NotAllowedError" || error.name === "PermissionDeniedError"
          ? "Camera access was denied. Allow it for this site in browser settings, then reload."
          : error.name === "NotFoundError"
            ? "No camera was found. Connect one or continue without the preview."
            : error.name === "NotReadableError" || error.name === "AbortError"
              ? "The camera is busy or failed to start. Close other apps using it, then retry."
              : "The camera could not start. Check this site's camera permission and try again.";
        setCameraError("Camera unavailable", detail);
        if (deviceBusy && retry < 2) window.setTimeout(() => { void startCamera(retry + 1); }, 1200);
        return false;
      } finally {
        cameraStartPromise = undefined;
      }
    })();
    return cameraStartPromise;
  }

  async function toggleCamera() {
    if (cameraStream) {
      stopCamera();
      try { localStorage.setItem("atulya.camera.on", "0"); } catch { /* ignore */ }
      return false;
    }
    try { localStorage.setItem("atulya.camera.on", "1"); } catch { /* ignore */ }
    return startCamera();
  }

  function setCameraError(label, detail) {
    cameraIssue = detail;
    const cameraLabel = cameraToggle?.querySelector(".preview-label b");
    if (cameraLabel) cameraLabel.innerHTML = darija("<i></i> CAMERA NEEDS ACCESS");
    setSystemTile("vision", "error", label);
    setSystemTile("issue", "error", detail);
    if (visionChannel) setChannelState(visionChannel, "off");
    setPhase("idle", label, detail);
  }

  function initializeGestureRecognition() {
    if (gestureModelReady && gestureRecognizer) return Promise.resolve();
    if (gestureInitializationPromise) return gestureInitializationPromise;
    gestureInitializationPromise = initializeGestureRecognitionNow().finally(() => { gestureInitializationPromise = undefined; });
    return gestureInitializationPromise;
  }

  async function initializeGestureRecognitionNow() {
    if (!gesturesEnabled || !cameraStream) return;
    const activeStream = cameraStream;
    gestureIssue = "";
    if (!cameraStream || !cameraFeed.videoWidth || !cameraFeed.videoHeight) {
      await new Promise((resolve) => cameraFeed.addEventListener("loadedmetadata", resolve, { once: true }));
    }
    try {
      const { FilesetResolver, GestureRecognizer } = await import("/api/runtime/mediapipe/vision_bundle.mjs");
      const vision = await FilesetResolver.forVisionTasks("/api/runtime/mediapipe/wasm");
      const options = {
        baseOptions: { modelAssetPath: "/api/models/gesture/gesture_recognizer.task", delegate: "GPU" },
        runningMode: "VIDEO",
        numHands: 1,
        minHandDetectionConfidence: 0.45,
        minHandPresenceConfidence: 0.45,
        minTrackingConfidence: 0.45,
      };
      try {
        gestureRecognizer = await GestureRecognizer.createFromOptions(vision, options);
      } catch {
        options.baseOptions.delegate = "CPU";
        gestureRecognizer = await GestureRecognizer.createFromOptions(vision, options);
      }
      if (!gesturesEnabled || cameraStream !== activeStream) {
        gestureRecognizer?.close?.(); gestureRecognizer = undefined;
        return;
      }
      gestureFrameErrors = 0;
      gestureModelReady = true;
      const gestureRegion = $("#gesture-region");
      const gestureChannel = $("#gesture-channel");
      if (gestureRegion) {
        gestureRegion.dataset.state = "live";
        gestureRegion.setAttribute("aria-label", darija("Gesture recognition active. Show open palm to stop speech, thumbs up for Yes, thumbs down for No, peace/victory to inspect scene."));
      }
      showGestureResult("SCANNING");
      syncGestureButton();
      if (gestureChannel) setChannelState(gestureChannel, "live");
      setSystemTile("gesture", "live", "Scanning for hand");
      scanGestures();
    } catch (error) {
      gestureModelReady = false;
      gestureIssue = `Gesture recognition failed: ${String(error.message || error.name || "Unknown error").slice(0, 200)}. Open Maintenance to check runtime assets.`;
      const gestureRegion = $("#gesture-region");
      const gestureChannel = $("#gesture-channel");
      showGestureResult("MODEL ERROR");
      if (gestureRegion) gestureRegion.dataset.state = "error";
      if (gestureChannel) setChannelState(gestureChannel, "setup");
      setSystemTile("gesture", "error", gestureIssue);
      const copy = $("#gesture-copy");
      if (copy) copy.title = darija(gestureIssue);
      document.dispatchEvent(new CustomEvent("atulya-device-status", { detail: { gesture: gestureIssue } }));
    }
  }

  function scanGestures() {
    if (!gesturesEnabled || !cameraStream || !gestureRecognizer) return;
    const now = performance.now();
    if (now - lastGestureFrameAt >= 100 && cameraFeed.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
      lastGestureFrameAt = now;
      try {
        const result = gestureRecognizer.recognizeForVideo(cameraFeed, now);
        gestureFrameErrors = 0;
        const category = result.gestures?.[0]?.[0];
        const categoryName = category && category.categoryName !== "None" && category.score >= 0.52 ? category.categoryName : "";
        updateGestureCommand(categoryName, category?.score || 0, now);
        const def = categoryName ? GESTURE_DEFINITIONS[categoryName] : null;
        const recognized = def && category.score >= 0.52
          ? `${def.icon} ${def.name} · ${Math.round(category.score * 100)}%` : "Scanning for hand";
        if (recognized !== (gestureCurrent || "Scanning for hand")) {
          gestureCurrent = recognized === "Scanning for hand" ? "" : recognized;
          const gestureRegion = $("#gesture-region");
          showGestureResult(recognized);
          if (gestureRegion) gestureRegion.dataset.state = gestureCurrent ? "detected" : "live";
          setSystemTile("gesture", "live", def ? `${recognized} ➜ ${def.action}` : recognized);
        }
      } catch {
        gestureFrameErrors += 1;
        if (gestureFrameErrors >= 10) {
          gestureIssue = "Gesture processing failed repeatedly. Turn gestures off and on to retry; camera preview remains available.";
          gestureRecognizer?.close?.(); gestureRecognizer = undefined; gestureModelReady = false;
          showGestureResult("RETRY NEEDED"); setSystemTile("gesture", "error", gestureIssue);
          document.dispatchEvent(new CustomEvent("atulya-device-status", { detail: { gesture: gestureIssue } }));
          return;
        }
        setSystemTile("gesture", "error", "Frame recognition failed");
      }
    }
    gestureFrame = requestAnimationFrame(scanGestures);
  }

  function updateGestureCommand(categoryName, score, now) {
    if (!categoryName || !GESTURE_DEFINITIONS[categoryName]) {
      if (!gestureNeutralSince) gestureNeutralSince = now;
      gestureCommandCandidate = "";
      gestureCommandCandidateSince = 0;
      updateGestureHUD("", 0, 0);
      if (now - gestureNeutralSince >= gestureReleaseMs) gestureCommandsArmed = true;
      return;
    }
    gestureNeutralSince = 0;
    if (score < gestureCommandThreshold) {
      gestureCommandCandidate = "";
      gestureCommandCandidateSince = 0;
      updateGestureHUD(categoryName, score, 0);
      return;
    }
    if (categoryName !== gestureCommandCandidate) {
      gestureCommandCandidate = categoryName;
      gestureCommandCandidateSince = now;
      updateGestureHUD(categoryName, score, 15);
      return;
    }
    const holdDuration = now - gestureCommandCandidateSince;
    const holdPct = Math.min(100, Math.round((holdDuration / gestureCommandHoldMs) * 100));
    updateGestureHUD(categoryName, score, holdPct);

    if (!gestureCommandsArmed || holdDuration < gestureCommandHoldMs || now - lastGestureCommandAt < gestureCommandCooldownMs) return;
    gestureCommandsArmed = false;
    lastGestureCommandAt = now;
    runGestureCommand(categoryName);
  }

  function runGestureCommand(categoryName) {
    const def = GESTURE_DEFINITIONS[categoryName];
    if (def) {
      showGestureToast(def.icon, def.name, def.action);
      showGestureResult(`${def.icon} ${def.name.toUpperCase()} · TRIGGERED`);
      setSystemTile("gesture", "live", `${def.icon} ${def.name} ➜ ${def.action}`);
    }

    if (categoryName === "Open_Palm") {
      if (voiceSessionActive || listening) {
        void cancelListening("Voice stopped by open palm.");
      } else if (speaking) {
        window.speechSynthesis?.cancel?.();
        speaking = false;
        clearSpokenReply();
        restoreIdlePhase("Speech stopped by open palm.");
      }
      return;
    }
    if (categoryName === "Pointing_Up") {
      if (!listening && !speaking) toggleListening();
      return;
    }
    if (categoryName === "Closed_Fist") {
      const player = document.getElementById("music-player");
      if (player) {
        player.querySelector("iframe")?.contentWindow?.postMessage('{"event":"command","func":"pauseVideo","args":""}', '*');
      }
      if (speaking) {
        window.speechSynthesis?.cancel?.();
        speaking = false;
        clearSpokenReply();
        restoreIdlePhase("Silenced by closed fist.");
      }
      return;
    }
    if (categoryName === "Victory") {
      void sendMessage("Please describe what you see in the camera frame right now.", voiceSessionActive, false);
      return;
    }
    if (categoryName === "ILoveYou") {
      void sendMessage("Jarvis, quick status report on all systems.", voiceSessionActive, false);
      return;
    }
    if (!brainReady || phase !== "idle") return;
    const affirmative = categoryName === "Thumb_Up";
    void sendMessage(affirmative ? "Yes" : "No", voiceSessionActive, false);
  }

  async function enableCamera() {
    if (cameraStream) return true;
    return Boolean(await toggleCamera());
  }

  function cameraCommand(text) {
    const value = text.trim().toLowerCase().replace(/[.!?]+$/, "");
    if (/^(?:please\s+)?(?:(?:turn|switch)\s+on|open|start|enable|activate)\s+(?:the\s+|my\s+)?camera$|^camera\s+on$|^(?:turn|switch)\s+(?:the\s+)?camera\s+on$/.test(value)) return true;
    if (/^(?:please\s+)?(?:(?:turn|switch)\s+off|close|stop|disable|deactivate)\s+(?:the\s+|my\s+)?camera$|^camera\s+off$|^(?:turn|switch)\s+(?:the\s+)?camera\s+off$/.test(value)) return false;
    return null;
  }

  // Only questions that need eyes send a camera frame (privacy + speed); they also switch the camera on.
  const VISION_INTENT = /\b(?:what do you see|what can you see|can you see|look at (?:this|that|me)|what(?:'s| is) (?:this|that) (?:in my hand|i'm holding|i am holding)|what am i holding|read (?:this|that|it)|scan (?:this|that)|describe (?:this|what you see|me)|how do i look|who is (?:this|that))\b|यह क्या है|ये क्या है|देखो|पढ़ो/i;
  function needsVision(text) { return VISION_INTENT.test(text); }

  function captureCameraFrame() {
    if (!visionReady || !cameraStream || !cameraFeed.videoWidth || !cameraFeed.videoHeight) return null;
    const scale = Math.min(1, 1280 / cameraFeed.videoWidth, 720 / cameraFeed.videoHeight);
    const frame = document.createElement("canvas");
    frame.width = Math.max(1, Math.round(cameraFeed.videoWidth * scale));
    frame.height = Math.max(1, Math.round(cameraFeed.videoHeight * scale));
    frame.getContext("2d", { alpha: false }).drawImage(cameraFeed, 0, 0, frame.width, frame.height);
    return frame.toDataURL("image/jpeg", 0.72);
  }


  // ---- Wake word and barge-in -------------------------------------------
  // Wake word: while live voice is on, utterances are transcribed locally and
  // ignored unless they start with "Hey Atulya" (or arrive within a short
  // follow-up window after Atulya spoke). Barge-in: while Atulya speaks, the
  // mic is monitored (with echo cancellation); talking over it stops speech
  // and starts listening immediately.
  const WAKE_PATTERN = /^\s*(?:(?:hey|hi|hello|ok|okay|ai|he|hay|हे|हाय|ओके)[\s,]+)?(?:atulya|atuliya|atulia|athulya|atulyaa|atul ya|a tulya|atuya|atulla|atoolya|atooliya|atulyah|atulea|अतुल्य|अतुल)(?=$|[\s,.!?:।-])[\s,.!?:।-]*/iu;
  const FOLLOW_UP_MS = 8000;
  const readFlag = (key, fallback) => {
    try { const value = localStorage.getItem(key); return value === null ? fallback : value === "1"; } catch { return fallback; }
  };
  // While the app is open the user is clearly talking to Atulya; the wake word is opt-in.
  let wakeWordEnabled = readFlag("atulya.voice.wake", false);
  // Voice-first: every reply is spoken unless muted.
  let voiceReplies = readFlag("atulya.voice.replies", true);
  let bargeInEnabled = readFlag("atulya.voice.bargein", true);
  let awakeUntil = 0;

  function updateVoiceRepliesButton() {
    const button = document.getElementById("voice-replies");
    if (!button) return;
    button.textContent = voiceReplies ? "🔊" : "🔇";
    button.setAttribute("aria-pressed", String(voiceReplies));
    button.title = darija(voiceReplies ? "Replies are spoken — tap to mute" : "Muted — tap to speak replies");
  }
  window.setTimeout(() => {
    updateVoiceRepliesButton();
    document.getElementById("voice-replies")?.addEventListener("click", () => {
      voiceReplies = !voiceReplies;
      setVoiceOption("atulya.voice.replies", voiceReplies);
      updateVoiceRepliesButton();
      if (!voiceReplies) releaseSpeech();
    });
  }, 0);

  function setVoiceOption(key, enabled) {
    try { localStorage.setItem(key, enabled ? "1" : "0"); } catch { /* storage unavailable */ }
  }

  // Returns the text to send, or null when the utterance should be ignored.
  // The user's own nickname for the assistant ("Tony") also wakes it on their devices.
  let nicknamePattern = null;
  async function loadNickname() {
    try {
      const { profile } = await (await fetch("/api/profile", { headers: { Accept: "application/json" } })).json();
      const nick = String(profile?.assistant_nickname || "").trim();
      const safe = nick.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      nicknamePattern = nick ? new RegExp(`^\\s*(?:(?:hey|hi|ok|okay|हे)[\\s,]+)?${safe}(?=$|[\\s,.!?:।-])[\\s,.!?:।-]*`, "iu") : null;
    } catch { nicknamePattern = null; }
  }

  function applyWakeWord(transcript) {
    if (!wakeWordEnabled) return transcript;
    const match = transcript.match(WAKE_PATTERN) || (nicknamePattern && transcript.match(nicknamePattern));
    if (match) {
      const rest = transcript.slice(match[0].length).trim();
      if (rest) return rest;
      awakeUntil = Date.now() + FOLLOW_UP_MS;
      return "";
    }
    if (Date.now() < awakeUntil) return transcript;
    return null;
  }

  function markFollowUpWindow() {
    if (wakeWordEnabled) awakeUntil = Date.now() + FOLLOW_UP_MS;
  }

  let bargeMonitor = null;
  async function startBargeMonitor() {
    if (bargeMonitor || !navigator.mediaDevices?.getUserMedia) return;
    const monitor = { stopped: false, stream: null, context: null };
    bargeMonitor = monitor;
    try {
      // Reuse the session's microphone: a second getUserMedia call makes Telegram/WebViews ask again.
      const live = microphoneStream?.getAudioTracks().some((track) => track.readyState === "live");
      if (!live) { bargeMonitor = null; return; }
      monitor.stream = microphoneStream;
      monitor.shared = true;
      if (monitor.stopped) return;
      const AudioContextType = window.AudioContext || window.webkitAudioContext;
      monitor.context = new AudioContextType();
      const analyser = monitor.context.createAnalyser();
      analyser.fftSize = 512;
      monitor.context.createMediaStreamSource(monitor.stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      let floor = 0.01;
      let loudSince = 0;
      const started = performance.now();
      const tick = () => {
        if (monitor.stopped) return;
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (const sample of samples) { const a = (sample - 128) / 128; sum += a * a; }
        const rms = Math.sqrt(sum / samples.length);
        const now = performance.now();
        // Learn the residual echo level for the first half second, then require
        // clearly louder speech held for 300 ms before interrupting.
        if (now - started < 500) floor = Math.max(floor, rms);
        else if (rms > Math.max(0.045, floor * 3)) {
          loudSince ||= now;
          if (now - loudSince > 300) { interruptSpeech(); return; }
        } else loudSince = 0;
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    } catch {
      stopBargeMonitor();
    }
  }

  function stopBargeMonitor() {
    const monitor = bargeMonitor;
    bargeMonitor = null;
    if (!monitor) return;
    monitor.stopped = true;
    if (!monitor.shared) monitor.stream?.getTracks().forEach((track) => track.stop());
    monitor.context?.close().catch(() => {});
  }

  function interruptSpeech() {
    stopBargeMonitor();
    if (!speaking) return;
    releaseSpeech();
    clearSpokenReply();
    awakeUntil = Date.now() + FOLLOW_UP_MS;
    setPhase("listening", "Listening", "Interrupted. Go ahead.");
    voiceSessionActive = true;
    startListening(true);
  }

  // Keep the monitor running exactly while Atulya is speaking in a live session.
  window.setInterval(() => {
    if (speaking && listening && !bargeInEnabled) cancelListening();
    const wanted = bargeInEnabled && voiceSessionActive && speaking && !listening;
    if (wanted && !bargeMonitor) startBargeMonitor();
    else if (!wanted && bargeMonitor) stopBargeMonitor();
  }, 120);

  function resumeLiveVoice() {
    if (!voiceSessionActive || listening) return;
    if (!voiceReady) {
      voiceSessionActive = false;
      return;
    }
    window.setTimeout(() => {
      if (voiceSessionActive && !listening && !speaking) startListening(true);
    }, 350);
  }

  // Never read emoji, markdown symbols or links aloud.
  function speakableText(text) {
    return String(text || "")
      .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{200D}]/gu, "")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/[*_`#>|~]+/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function speakWithBrowser(rawText, detail = "Using the browser's built-in speech voice.") {
    const text = speakableText(rawText);
    if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
      speaking = false;
      clearSpokenReply();
      setPhase("idle", "Voice unavailable", "This browser cannot play the reply aloud. The text reply is still here.");
      resumeLiveVoice();
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    const hindi = /\p{Script=Devanagari}/u.test(text);
    const arabic = /\p{Script=Arabic}/u.test(text);
    const targetLanguage = hindi ? "hi-IN" : arabic ? "ar-MA" : "en-IN";
    utterance.lang = targetLanguage;
    activeUtterance = utterance;
    preferMaleVoice(utterance, targetLanguage);
    window.speechSynthesis.addEventListener?.("voiceschanged", () => {
      if (activeUtterance === utterance) preferMaleVoice(utterance, targetLanguage);
    }, { once: true });
    utterance.onstart = () => {
      speaking = true;
      setPhase("speaking", "Speaking", detail);
      refreshWave();
    };
    utterance.onerror = () => {
      if (activeUtterance !== utterance) return;
      activeUtterance = undefined;
      speaking = false;
      clearSpokenReply();
      setPhase("idle", "Voice unavailable", "The browser couldn't play the reply aloud. The text reply is still here.");
      resumeLiveVoice();
    };
    utterance.onend = () => {
      if (activeUtterance !== utterance) return;
      activeUtterance = undefined;
      speaking = false;
      clearSpokenReply();
      restoreIdlePhase();
      markFollowUpWindow();
      resumeLiveVoice();
      refreshWave();
    };
    window.speechSynthesis.cancel();
    try {
      window.speechSynthesis.speak(utterance);
    } catch {
      activeUtterance = undefined;
      speaking = false;
      setPhase("idle", "Voice unavailable", "The browser couldn't start speech playback. The text reply is still here.");
    }
  }

  function preferMaleVoice(utterance, targetLanguage) {
    const voices = window.speechSynthesis?.getVoices?.() || [];
    const language = targetLanguage.split("-")[0].toLowerCase();
    const matching = voices.filter((voice) => voice.lang?.toLowerCase().startsWith(language));
    const maleNames = language === "hi"
      ? /male|hemant|madhur|ravi|amit|arjun|rahul|aditya/i
      : /male|david|mark|ryan|guy|eric|brian|daniel|george|james|thomas|alex|fred|aaron/i;
    const preferred = matching.find((voice) => maleNames.test(voice.name));
    if (preferred) {
      utterance.voice = preferred;
      utterance.lang = preferred.lang;
    } else if (matching[0]) {
      utterance.lang = matching[0].lang;
    }
  }

  function greet() {
    if (greeted || !healthLoaded || !brainReady || !sceneReady || !historyReady) return;
    greeted = true;
    const returningSession = messagesNode.querySelectorAll(".chat-message.user, .chat-message.assistant").length > 0;
    // A restored conversation already has its history on screen: greet by voice only, don't add another bubble.
    const hour = new Date().getHours();
    // قاعدة واحدة : Atulya كتهضر غير بالدارجة بحروف عربية، حتى فالتحية المكتوبة محلياً.
    const timeGreet = hour < 12 ? "صباح الخير." : "مساء الخير.";
    const greeting = returningSession ? "مرحبا بعودتك." : timeGreet;
    if (!returningSession) {
      const greetingBubble = appendMessage("assistant", greeting, null, true);
      conversation.push({ role: "assistant", content: greeting });
      highlightSpokenReply(greetingBubble);
    }
    // Speak only after the scene is ready, then open the mic automatically.
    // The browser still owns the permission prompt; Atulya never bypasses it.
    // Inside Telegram the mic starts when the user taps the voice wave (Telegram asks for permission per open).
    voiceSessionActive = voiceReady && !window.Telegram?.WebApp?.initData;
    speak(greeting);
    deliverMorningBriefing();
    // Auto-start mic if permission already granted (no extra click needed).
    if (voiceSessionActive && navigator.permissions) {
      navigator.permissions.query({ name: "microphone" }).then((result) => {
        if (result.state === "granted") {
          window.setTimeout(() => { if (voiceSessionActive && !listening) startListening(true); }, 800);
        }
      }).catch(() => {});
    }
  }

  // First visit of the day: show and read the morning briefing once the greeting ends.
  async function deliverMorningBriefing() {
    let body;
    try {
      const response = await fetch("/api/briefing", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ conversation_id: conversationId }),
      });
      if (!response.ok) return;
      body = await response.json();
    } catch {
      return;
    }
    const text = String(body?.text || "").trim();
    if (!text) return;
    const deadline = Date.now() + 20000;
    while ((speaking || phase === "thinking") && Date.now() < deadline) await new Promise((resolve) => setTimeout(resolve, 300));
    const bubble = appendMessage("assistant", text);
    for (const item of body.links || []) {
      try {
        const url = new URL(item.url);
        if (url.protocol !== "https:") continue;
        const link = document.createElement("a"); link.href = url.href;
        link.textContent = item.label; link.target = "_blank"; link.rel = "noopener noreferrer";
        bubble.append(link);
      } catch { /* Ignore malformed provider links. */ }
    }
    conversation.push({ role: "assistant", content: text });
    if (listening) return; // the user already started talking; leave it on screen
    highlightSpokenReply(bubble);
    await speak(text);
  }

  function releaseSpeech() {
    activeAudioRequest += 1;
    activeAudio?.pause();
    activeAudio = undefined;
    speechAnalyser = undefined;
    if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);
    activeAudioUrl = undefined;
    speaking = false;
    activeUtterance = undefined;
    window.speechSynthesis?.cancel();
    refreshWave();
  }

  // Sentence-pipelined speech: each sentence is synthesized as soon as it is
  // pushed (while earlier ones play), so the first words start almost
  // immediately instead of after the whole reply has been generated.
  function createSpeechStream(mode = "text") {
    const requestId = ++activeAudioRequest;
    const pending = [];
    let closed = false;
    let wake;
    let failedText = "";
    let synthChain = Promise.resolve();
    const cancelled = () => requestId !== activeAudioRequest;
    const synthesize = (text) => fetch("/api/voice/synthesize", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "audio/wav" },
      body: JSON.stringify({ text, language: "auto", mode }),
    }).then((response) => {
      if (!response.ok) throw new Error("Local speech generation failed");
      return response.blob();
    });
    const playBlob = (blob) => new Promise((resolve, reject) => {
      activeAudioUrl = URL.createObjectURL(blob);
      activeAudio = new Audio(activeAudioUrl);
      speechAudioContext ||= new (window.AudioContext || window.webkitAudioContext)();
      speechAudioContext.resume().then(() => {
        const source = speechAudioContext.createMediaElementSource(activeAudio);
        speechAnalyser = speechAudioContext.createAnalyser();
        speechAnalyser.fftSize = 512;
        source.connect(speechAnalyser);
        speechAnalyser.connect(speechAudioContext.destination);
        activeAudio.onplay = () => {
          speaking = true;
          setPhase("speaking", "Speaking", "كيتنطق بالصوت المحلي ديال أتوليا.");
          refreshWave();
        };
        const cleanup = () => {
          activeAudio = undefined;
          speechAnalyser = undefined;
          if (activeAudioUrl) URL.revokeObjectURL(activeAudioUrl);
          activeAudioUrl = undefined;
        };
        activeAudio.onended = () => { cleanup(); resolve(); };
        activeAudio.onerror = () => { cleanup(); reject(new Error("playback failed")); };
        return activeAudio.play();
      }).catch(reject);
    });
    const done = (async () => {
      while (true) {
        if (!pending.length) {
          if (closed) break;
          await new Promise((resolve) => { wake = resolve; });
          continue;
        }
        const item = pending.shift();
        if (cancelled()) return;
        if (failedText) { failedText += ` ${item.text}`; continue; }
        try {
          const blob = await item.audio;
          if (cancelled()) return;
          await playBlob(blob);
        } catch {
          if (cancelled()) return;
          failedText = item.text;
        }
      }
      if (cancelled()) return;
      if (failedText) {
        speakWithBrowser(failedText, "Local voice is unavailable; using the browser voice.");
        return;
      }
      speaking = false;
      clearSpokenReply();
      restoreIdlePhase();
      markFollowUpWindow();
      resumeLiveVoice();
      refreshWave();
    })();
    return {
      push(text) {
        const clean = String(text || "").trim();
        if (!clean || closed || cancelled()) return;
        // One synthesis at a time, in order: parallel requests share the server's CPUs and
        // delay the first sentence until all of them finish.
        const audio = synthChain.catch(() => {}).then(() => (cancelled() ? null : synthesize(clean)));
        synthChain = audio;
        const item = { text: clean, audio };
        item.audio.catch(() => {});
        pending.push(item);
        wake?.();
      },
      finish() {
        closed = true;
        wake?.();
        return done;
      },
    };
  }

  // Split streamed text into speakable sentences; returns [complete sentences, remainder].
  function takeSentences(buffer, flush = false) {
    const sentences = [];
    const pattern = /[.!?।]+["')\]]*\s+|\n+/g;
    let consumed = 0;
    let match;
    while ((match = pattern.exec(buffer))) {
      const sentence = buffer.slice(consumed, pattern.lastIndex).trim();
      if (sentence.length >= 2) sentences.push(sentence);
      consumed = pattern.lastIndex;
    }
    let rest = buffer.slice(consumed);
    // Start speaking a long first clause at a comma instead of waiting for the full sentence.
    if (!flush && !sentences.length && rest.length > 80) {
      const comma = rest.lastIndexOf(", ", 100);
      if (comma > 24) {
        sentences.push(rest.slice(0, comma).trim());
        rest = rest.slice(comma + 2);
      }
    }
    if (flush && rest.trim()) {
      sentences.push(rest.trim());
      rest = "";
    }
    return [sentences, rest];
  }

  function speak(text) {
    if (!localTtsReady) {
      speakWithBrowser(text, "Speaking with this browser's built-in voice.");
      return;
    }
    const stream = createSpeechStream();
    const [sentences] = takeSentences(`${text} `, true);
    sentences.forEach((sentence) => stream.push(sentence));
    return stream.finish();
  }

  function parseLayoutCommand(text) {
    const command = text.toLowerCase()
      .replace(/[.!?,]/g, " ")
      .replace(/^(?:(?:hey|okay|ok)\s+)?atulya\s+/, "")
      .replace(/^(?:can|could|would) you\s+/, "")
      .replace(/\b(the|my|side|right|left|please|box)\b/g, " ")
      .replace(/\s+/g, " ").trim();
    if (/^(restore|reset) (?:the )?layout$|^(show|restore) all (?:the )?(?:panels|sections)$/.test(command)) return { type: "restore" };
    if (/^(?:exit|leave|close) (?:the )?(?:camera )?(?:full ?screen|focus)(?: view)?$|^go back to (?:the )?normal layout$/.test(command)) return { type: "exit-focus" };
    if (/^(?:(?:show|open|go to|make) (?:it )?)?(?:full ?screen|fullscreen) (?:the )?(?:camera|camera preview)$|^(?:show|open) (?:the )?(?:camera|camera preview) (?:full ?screen|fullscreen)$/.test(command)) return { type: "focus-camera" };
    if (/^(?:(?:show|open|go to|make) (?:it )?)?(?:full ?screen|fullscreen) (?:the )?(?:system )?status(?: panel| section)?$|^(?:show|open) (?:the )?(?:system )?status(?: panel| section)? (?:full ?screen|fullscreen)$/.test(command)) return { type: "focus-status" };
    if (/^(?:start |open |go to |enable |switch to )?(?:conversation|talk|talking|voice|hands ?free) mode$|^(?:only|just) (?:show )?(?:the )?hologram$|^full ?screen hologram$|^chat (?:chupao|chhupao|band karo|hatao)$/.test(command)) {
      return { type: "panel", name: "chat", visible: false };
    }
    if (/^(?:exit|stop|close|leave) (?:conversation|talk|voice) mode$|^chat (?:dikhao|kholo|wapas)$/.test(command)) return { type: "panel", name: "chat", visible: true };
    const panel = command.match(/^(show|open|display|add|hide|remove|close|minimi[sz]e|collapse|bring back) (camera(?: preview)?|chat|chats|conversation|messages|text|system status|status|system)(?: (?:preview|panel|section|window|area|options?|screen|part|view|bar))*$/);
    if (panel) {
      const name = panel[2].startsWith("camera") ? "camera" : ["chat", "chats", "conversation", "messages", "text"].includes(panel[2]) ? "chat" : "status";
      return { type: "panel", name, visible: ["show", "open", "display", "add", "bring back"].includes(panel[1]) };
    }
    if (/^(?:add|show) (?:a )?(?:new )?section\b/.test(command)) return { type: "unknown-section" };
    return null;
  }

  function showLayoutToast(message) {
    if (!layoutToast) return;
    layoutToast.textContent = message;
    layoutToast.hidden = false;
    window.clearTimeout(layoutToastTimer);
    layoutToastTimer = window.setTimeout(() => { layoutToast.hidden = true; }, 4200);
  }

  function exitFocusedLayout() {
    document.body.classList.remove("camera-focus", "status-focus");
    if (layoutFocusExit) layoutFocusExit.hidden = true;
  }

  function syncLayoutControls() {
    if (layoutVoiceToggle) {
      layoutVoiceToggle.hidden = !document.body.classList.contains("panel-chat-hidden");
      layoutVoiceToggle.textContent = darija(voiceSessionActive ? "STOP VOICE" : "VOICE");
      layoutVoiceToggle.setAttribute("aria-label", darija(voiceSessionActive ? "Stop live voice conversation" : "Start live voice conversation"));
    }
    if (layoutChatToggle) layoutChatToggle.hidden = !document.body.classList.contains("panel-chat-hidden");
  }

  // ---- Device location (asked only when a question needs it; refreshed silently once allowed) ----
  function sendDeviceLocation({ prompt = false } = {}) {
    return new Promise((resolve) => {
      if (!navigator.geolocation) { resolve(false); return; }
      navigator.geolocation.getCurrentPosition(async (position) => {
        try {
          const response = await fetch("/api/location", {
            method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ latitude: position.coords.latitude, longitude: position.coords.longitude,
              accuracy: position.coords.accuracy, source: window.AtulyaNative ? "app" : "browser" }),
          });
          resolve(response.ok);
        } catch { resolve(false); }
      }, () => {
        if (prompt) showLayoutToast("Location not shared. You can name a city instead.");
        resolve(false);
      }, { enableHighAccuracy: false, timeout: 12000, maximumAge: 5 * 60 * 1000 });
    });
  }
  async function refreshLocationIfAllowed() {
    if (document.hidden) return; // battery: never in the background, never continuous tracking
    try {
      const state = await navigator.permissions?.query({ name: "geolocation" });
      if (state?.state === "granted") sendDeviceLocation();
    } catch { /* permissions API unavailable */ }
  }
  window.setTimeout(refreshLocationIfAllowed, 4000);
  window.setInterval(refreshLocationIfAllowed, 30 * 60 * 1000);
  let locationRetry = "";
  async function shareLocationAndRetry() {
    const question = [...conversation].reverse().find((item) => item.role === "user")?.content || "";
    if (!question || locationRetry === question) return; // re-ask once, never loop
    locationRetry = question;
    if (await sendDeviceLocation({ prompt: true })) {
      for (let waited = 0; chatInFlight > 0 && waited < 60000; waited += 250) {
        await new Promise((resolve) => setTimeout(resolve, 250)); // let the current reply finish first
      }
      sendMessage(question, voiceReplies && voiceSessionActive);
    }
  }

  // Screen actions requested by the brain (tool screen_control), so any phrasing works.
  function runScreenAction(action) {
    if (action && typeof action === "object" && action.type === "link") {
      let url;
      try { url = new URL(action.url); } catch { return; }
      if (url.protocol !== "https:" || url.username || url.password) return;
      const card = document.createElement("article"); card.className = "chat-message notice";
      const link = document.createElement("a"); link.href = url.href;
      link.textContent = darija(action.label || "Open website");
      link.target = /Android/i.test(navigator.userAgent) || window.AtulyaNative ? "_self" : "_blank";
      link.rel = "noopener noreferrer";
      card.append(link); messagesNode.append(card); messagesNode.scrollTop = messagesNode.scrollHeight;
      return;
    }
    const actions = {
      hide_chat: () => setConversationMode(true),
      conversation_mode: () => setConversationMode(true),
      show_chat: () => setConversationMode(false),
      new_chat: () => document.getElementById("new-conversation")?.click(),
      open_history: () => { setConversationMode(false); document.getElementById("open-history")?.click(); },
      open_settings: () => { setConversationMode(false); const menu = document.querySelector(".account-menu"); if (menu) menu.open = true; },
      camera_on: () => enableCamera(),
      camera_off: () => stopCamera(),
      voice_replies_on: () => { if (!voiceReplies) document.getElementById("voice-replies")?.click(); },
      voice_replies_off: () => { if (voiceReplies) document.getElementById("voice-replies")?.click(); },
      reload: () => window.setTimeout(() => window.location.reload(), 1500),
      share_location: () => shareLocationAndRetry(),
    };
    const fail = (detail) => appendMessage("notice", `That screen action didn't work (${action}): ${detail}`, null, false);
    if (!actions[action]) { fail("this screen doesn't support it"); return; }
    try {
      const result = actions[action]();
      if (result && typeof result.catch === "function") result.catch(error => fail(error?.message || "it failed"));
    } catch (error) { fail(error?.message || "it failed"); }
  }

  // Android Back button (MainActivity asks this first): close what is open instead of leaving the app.
  window.atulyaBack = () => {
    const menu = document.querySelector(".account-menu[open]");
    if (menu) { menu.open = false; return true; }
    const dialog = [...document.querySelectorAll("dialog[open]")].find((item) => item.id !== "auth-dialog");
    if (dialog) { dialog.close(); return true; }
    if (document.body.classList.contains("panel-chat-hidden")) { setConversationMode(false); return true; }
    if (document.body.classList.contains("camera-focus") || document.body.classList.contains("status-focus")) {
      exitFocusedLayout();
      return true;
    }
    return false;
  };

  // Conversation mode (like ChatGPT/Claude voice): hide the chat, keep it recorded, and keep listening.
  async function setConversationMode(on) {
    document.body.classList.toggle("panel-chat-hidden", on);
    exitFocusedLayout();
    if (on && voiceReady && !voiceSessionActive && !listening) await toggleListening();
    syncLayoutControls();
  }

  async function applyLayoutCommand(command) {
    if (command.type === "unknown-section") return "I can show or hide the existing camera, chat, and system status panels. To add another section, tell me what information it should display.";
    if (command.type === "restore") {
      document.body.classList.remove("panel-camera-hidden", "panel-chat-hidden", "panel-status-hidden", "camera-focus", "status-focus");
      if (layoutFocusExit) layoutFocusExit.hidden = true;
      syncLayoutControls();
      return "All Atulya panels are back in their usual places.";
    }
    if (command.type === "exit-focus") {
      exitFocusedLayout();
      return "Back to the usual Atulya layout.";
    }
    if (command.type === "focus-camera") {
      if (!await enableCamera()) return "The camera could not start. Check camera access, then try again.";
      document.body.classList.remove("status-focus", "panel-camera-hidden");
      document.body.classList.add("camera-focus");
      if (layoutFocusExit) layoutFocusExit.hidden = false;
      return "Camera is full screen with gestures beside it. Say exit focus or press Escape to return.";
    }
    if (command.type === "focus-status") {
      document.body.classList.remove("camera-focus", "panel-status-hidden");
      document.body.classList.add("status-focus");
      if (layoutFocusExit) layoutFocusExit.hidden = false;
      return "System status is full screen. Say exit focus or press Escape to return.";
    }
    const className = { camera: "panel-camera-hidden", chat: "panel-chat-hidden", status: "panel-status-hidden" }[command.name];
    exitFocusedLayout();
    if (command.name === "camera" && command.visible) {
      document.body.classList.remove(className);
      const enabled = await enableCamera();
      return enabled ? "Camera preview shown." : "Camera panel shown, but the camera could not start. Check camera access and try again.";
    }
    if (command.name === "chat") await setConversationMode(!command.visible);
    else document.body.classList.toggle(className, !command.visible);
    syncLayoutControls();
    const label = { camera: "camera preview", chat: "chat", status: "system status" }[command.name];
    if (command.name === "camera" && !command.visible) return "Camera preview hidden; the camera stays on for gestures. Say camera off to stop the camera.";
    return `${label[0].toUpperCase()}${label.slice(1)} ${command.visible ? "shown" : "hidden"}.`;
  }

  layoutFocusExit?.addEventListener("click", exitFocusedLayout);
  layoutVoiceToggle?.addEventListener("click", async () => { await toggleListening(); syncLayoutControls(); });
  layoutChatToggle?.addEventListener("click", () => setConversationMode(false));
  talkModeButton?.addEventListener("click", () => setConversationMode(true));

  let chatInFlight = 0;
  async function sendMessage(...args) {
    chatInFlight += 1;
    try { return await sendMessageNow(...args); } finally { chatInFlight -= 1; }
  }

  async function sendMessageNow(text, speakReply = false, includeVision = null, mode = "text") {
    if (includeVision === null) includeVision = needsVision(String(text || ""));
    if (includeVision && !cameraStream) {
      const started = await enableCamera();
      if (started) await new Promise((resolve) => setTimeout(resolve, 1200)); // let the first frame arrive
    }
    const cleanText = text.trim();
    if (!cleanText) return;
    appendMessage("user", cleanText);
    conversation.push({ role: "user", content: cleanText });
    while (conversation.length > 38) conversation.shift();
    prompt.value = "";
    const quick = cleanText.toLowerCase().replace(/[.!?।]/g, "").trim();
    if (/^(?:stop|stop talking|quiet|chup|bas|enough|shant)$/.test(quick)) {
      releaseSpeech();
      const reply = "Stopped.";
      appendMessage("assistant", reply);
      setPhase("idle", "Ready", reply);
      return;
    }
    if (/^(?:repeat|say that again|phir se bolo|repeat that)$/.test(quick)) {
      const last = [...conversation].reverse().find((item) => item.role === "assistant" && item !== conversation.at(-1))?.content
        || [...conversation].reverse().find((item) => item.role === "assistant")?.content
        || "";
      const reply = last || "I have nothing to repeat yet.";
      const assistantMessage = appendMessage("assistant", reply);
      conversation.push({ role: "assistant", content: reply });
      if (speakReply && last) {
        highlightSpokenReply(assistantMessage);
        await speak(reply);
      } else setPhase("idle", "Ready", reply);
      return;
    }
    if (/^(?:what can you do|help|commands)$/.test(quick)) {
      const reply = "Voice commands: weather, news, hide chat, show chat, mute, unmute, stop, repeat, camera on, wake word on, add a weekday 8:00 briefing, places near me. The hologram follows listening, thinking, and speaking.";
      const assistantMessage = appendMessage("assistant", reply);
      conversation.push({ role: "assistant", content: reply });
      if (speakReply) {
        highlightSpokenReply(assistantMessage);
        await speak(reply);
      } else setPhase("idle", "Ready", reply);
      return;
    }
    const layoutCommand = parseLayoutCommand(cleanText);
    if (layoutCommand) {
      const reply = await applyLayoutCommand(layoutCommand);
      const assistantMessage = appendMessage("assistant", reply);
      conversation.push({ role: "assistant", content: reply });
      if (speakReply) {
        highlightSpokenReply(assistantMessage);
        await speak(reply);
      } else {
        setPhase("idle", "Layout updated", reply);
        showLayoutToast(reply);
      }
      return;
    }
    const approval = approvalAnswer(cleanText);
    if (approval !== null) {
      const [latest] = [...pendingActions.keys()].slice(-1);
      setPhase("thinking", approval ? "Working" : "Cancelling", approval ? "Running the approved action." : "Cancelling the request.");
      const reply = await decideAction(latest, approval);
      if (speakReply && reply) await speak(reply);
      else setPhase("idle", "Ready", reply || "");
      return;
    }
    const muteCommand = cleanText.toLowerCase().match(/^(?:mute|unmute|voice (?:on|off)|stop speaking replies|speak replies)$/);
    if (muteCommand) {
      voiceReplies = !/^(?:mute|voice off|stop speaking replies)$/.test(muteCommand[0]);
      setVoiceOption("atulya.voice.replies", voiceReplies);
      updateVoiceRepliesButton();
      const reply = darija(voiceReplies ? "I'll speak my replies." : "Muted. I'll reply in text only.");
      appendMessage("assistant", reply);
      setPhase("idle", "Ready", reply);
      return;
    }
    const voiceOption = cleanText.toLowerCase().match(/^(?:turn |switch )?(wake ?word|interrupt(?:ion)?s?|barge[ -]?in)\s+(on|off)$|^(?:turn |switch )?(on|off)\s+(?:the )?(wake ?word|interrupt(?:ion)?s?|barge[ -]?in)$/);
    if (voiceOption) {
      const name = voiceOption[1] || voiceOption[4];
      const enabled = (voiceOption[2] || voiceOption[3]) === "on";
      if (/wake/.test(name)) { wakeWordEnabled = enabled; setVoiceOption("atulya.voice.wake", enabled); }
      else { bargeInEnabled = enabled; setVoiceOption("atulya.voice.bargein", enabled); }
      const reply = /wake/.test(name)
        ? enabled ? "Wake word is on. Start with “Hey Atulya”." : "Wake word is off. I'll answer everything I hear."
        : enabled ? "Interrupting is on. Talk over me to stop me." : "Interrupting is off.";
      appendMessage("assistant", reply);
      conversation.push({ role: "assistant", content: reply });
      setPhase("idle", "Ready", reply);
      return;
    }
    const cameraEnabled = cameraCommand(cleanText);
    if (cameraEnabled !== null) {
      const enabled = cameraEnabled ? await enableCamera() : (stopCamera(), true);
      const reply = cameraEnabled
        ? enabled ? "Camera preview is on. Atulya is not analyzing the video yet." : "Camera preview could not start. Check camera permission or availability."
        : "Camera preview is off.";
      const assistantMessage = appendMessage("assistant", reply);
      conversation.push({ role: "assistant", content: reply });
      if (speakReply) {
        highlightSpokenReply(assistantMessage);
        await speak(reply);
      } else setPhase("idle", enabled ? "Camera preview on" : "Camera preview off", reply);
      return;
    }
    setPhase("thinking", "Thinking", "Working on your message.");
    let serviceUnavailable = false;
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream, application/json" },
        body: JSON.stringify({ messages: mode === "voice" ? conversation.slice(-9) : conversation, image: includeVision ? captureCameraFrame() : null, conversation_id: conversationId, stream: true, mode }),
      });
      if (!response.ok) {
        if (response.status === 401) { await refreshAuthState(); throw new Error("Please sign in again to continue."); }
        if ([404, 405].includes(response.status) && selfHealReload()) return;
        const body = await response.json().catch(() => ({}));
        serviceUnavailable = [404, 405, 503].includes(response.status);
        const message = [404, 405].includes(response.status)
          ? "Atulya was just updated. Reload the page once to continue."
          : response.status === 503
            ? "Chat is unavailable right now. You can still use the scene and camera preview."
            : "Atulya couldn't complete that message. Please try again.";
        throw new Error(message);
      }
      let reply = "";
      let assistantMessage = null;
      let speechStream = null;
      let speechBuffer = "";
      if (response.headers.get("content-type")?.includes("text/event-stream")) {
        if (!response.body) throw new Error("Atulya's reply stream was unavailable.");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let pending = "";
        let streamError = "";
        const processEvent = (raw) => {
          const dataLine = raw.split(/\r?\n/).find((line) => line.startsWith("data:"));
          if (!dataLine) return;
          const event = JSON.parse(dataLine.slice(5).trim());
          if (event.error) streamError = String(event.error);
          if (event.confirm) showActionRequest(event.confirm);
          if (event.ui) runScreenAction(event.ui);
          if (typeof event.text === "string" && event.text) {
            reply += event.text;
            if (speakReply && localTtsReady) {
              if (!speechStream) speechStream = createSpeechStream(mode);
              let [sentences, rest] = takeSentences(speechBuffer + event.text);
              // First audio fast: speak the opening clause (comma or ~8 words) instead of waiting for
              // the whole first sentence; server voice time grows with length (~0.15 s per word).
              if (!speechStream.started && !sentences.length) {
                const clause = rest.match(/^(.{12,}?[,;:—])\s+/) || rest.match(/^((?:\S+\s+){8})/);
                if (clause) { sentences = [clause[1].trim()]; rest = rest.slice(clause[0].length); }
              }
              if (sentences.length) speechStream.started = true;
              speechBuffer = rest;
              sentences.forEach((sentence) => speechStream.push(sentence));
            }
            if (!assistantMessage) assistantMessage = appendMessage("assistant", "", null, false);
            assistantMessage.textContent = reply;
            messagesNode.scrollTop = messagesNode.scrollHeight;
          }
        };
        while (true) {
          const { value, done } = await reader.read();
          pending += decoder.decode(value || new Uint8Array(), { stream: !done });
          let boundary;
          while ((boundary = pending.indexOf("\n\n")) >= 0) {
            processEvent(pending.slice(0, boundary).replace(/\r$/, ""));
            pending = pending.slice(boundary + 2);
          }
          if (done) break;
        }
        if (pending.trim()) processEvent(pending);
        if (streamError) throw new Error(streamError);
        if (assistantMessage) saveMessage(assistantMessage);
      } else {
        const body = await response.json().catch(() => ({}));
        reply = String(body.text || "").trim();
        assistantMessage = reply ? appendMessage("assistant", reply) : null;
        (body.confirm || []).forEach(showActionRequest);
      }
      reply = reply.trim();
      if (!reply) throw new Error("Atulya returned an empty response.");
      conversation.push({ role: "assistant", content: reply });
      if (speakReply && speechStream) {
        highlightSpokenReply(assistantMessage);
        takeSentences(speechBuffer, true)[0].forEach((sentence) => speechStream.push(sentence));
        await speechStream.finish();
      } else if (speakReply) {
        highlightSpokenReply(assistantMessage);
        await speak(reply);
      }
      else setPhase("idle", "Ready", "Atulya replied in chat.");
    } catch (error) {
      const message = error.message || "Atulya could not complete that reply.";
      if (speakReply && serviceUnavailable) voiceSessionActive = false;
      setPhase("idle", serviceUnavailable ? "Chat unavailable" : "Reply unavailable", message);
      appendMessage("notice", message);
      if (speakReply) {
        if (!serviceUnavailable) resumeLiveVoice();
      }
    }
  }

  // Between turns keep the microphone stream (no new permission prompt); only drop the recorder/analyser.
  async function pauseMicrophone() {
    if (!voiceSessionActive) return releaseMicrophone();
    if (microphoneContext) await microphoneContext.close().catch(() => {});
    microphoneContext = undefined;
    microphoneAnalyser = undefined;
    recorder = undefined;
    refreshWave();
  }

  // Pause keeps the granted stream muted for a while instead of stopping it: stopping makes
  // Telegram/WebViews ask for permission again on the next tap. Fully released after 10 idle minutes.
  let microphoneHoldTimer = 0;
  async function holdMicrophone() {
    microphoneStream?.getAudioTracks().forEach((track) => { track.enabled = false; });
    if (microphoneContext) await microphoneContext.close().catch(() => {});
    microphoneContext = undefined;
    microphoneAnalyser = undefined;
    recorder = undefined;
    clearTimeout(microphoneHoldTimer);
    microphoneHoldTimer = setTimeout(() => { if (!voiceSessionActive) releaseMicrophone(); }, 10 * 60 * 1000);
    refreshWave();
  }

  async function releaseMicrophone() {
    clearTimeout(microphoneHoldTimer);
    if (microphoneStream) microphoneStream.getTracks().forEach((track) => track.stop());
    microphoneStream = undefined;
    if (microphoneContext) await microphoneContext.close().catch(() => {});
    microphoneContext = undefined;
    microphoneAnalyser = undefined;
    recorder = undefined;
    refreshWave();
  }

  function stopRecorder() {
    const activeRecorder = recorder;
    if (!activeRecorder || activeRecorder.state === "inactive") return Promise.resolve(new Blob(recorderChunks, { type: recordingMime }));
    return new Promise((resolve) => {
      activeRecorder.addEventListener("stop", () => resolve(new Blob(recorderChunks, { type: recordingMime })), { once: true });
      try { activeRecorder.stop(); } catch { resolve(new Blob(recorderChunks, { type: recordingMime })); }
    });
  }

  async function finishListening() {
    if (!listening || !recorder) return;
    const activeRequest = voiceRequest;
    listening = false;
    const audio = await stopRecorder();
    await pauseMicrophone();
    if (activeRequest !== voiceRequest) return;
    if (!audio.size) {
      setPhase("idle", "No voice heard", "Try speaking again or type below.");
      resumeLiveVoice();
      return;
    }
    setPhase("thinking", "Understanding", "Turning your speech into text.");
    try {
      const formData = new FormData();
      formData.append("audio", audio, recordingMime.includes("webm") ? "message.webm" : "message.audio");
      // Let Whisper detect the spoken language, including mixed Hindi and English.
      const response = await fetch("/api/voice/transcribe", { method: "POST", body: formData });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 401) { await refreshAuthState(); throw new Error("Please sign in again to continue."); }
        if ([404, 405].includes(response.status) && selfHealReload()) return;
        const backendDetail = typeof body.detail === "string" ? body.detail.trim() : "";
        const message = [404, 405].includes(response.status)
          ? "Atulya was just updated. Reload the page once to continue."
          : response.status === 503
            ? backendDetail || "Local speech recognition is unavailable. Finish voice setup, then restart Atulya."
            : "Speech recognition failed. Try again or type below.";
        throw new Error(message);
      }
      const heard = String(body.text || "").trim();
      const transcript = heard ? applyWakeWord(heard) : "";
      if (transcript === null || (!heard && wakeWordEnabled)) {
        // Not addressed to Atulya: keep waiting quietly for the wake word.
        setPhase("idle", "Say “Hey Atulya”", "Waiting for the wake word. Everything stays on this device.");
        resumeLiveVoice();
        return;
      }
      if (!heard) throw new Error("No speech was recognized. Try again or type below.");
      if (!transcript) {
        setPhase("listening", "Yes?", "I'm listening.");
        resumeLiveVoice();
        return;
      }
      await sendMessage(transcript, true, null, "voice");
    } catch (error) {
      setPhase("idle", "I missed that", error.message || "Speech recognition failed. You can type below.");
      appendMessage("notice", error.message || "Local speech recognition failed.");
      if (voiceReady) resumeLiveVoice();
      else voiceSessionActive = false;
    }
  }

  async function cancelListening(message = "Voice capture stopped.") {
    nativeVoice?.postMessage(JSON.stringify({ cmd: "stop" }));
    voiceRequest += 1;
    voiceSessionActive = false;
    listening = false;
    if (recorder && recorder.state !== "inactive") {
      recorder.ondataavailable = null;
      try { recorder.stop(); } catch {}
    }
    recorderChunks = [];
    await holdMicrophone();
    window.speechSynthesis?.cancel?.();
    releaseSpeech();
    restoreIdlePhase(message);
  }

  // ---- Android app: the phone's own speech recognizer (window.AtulyaNative, Atulya origin only) ----
  // More accurate than the server's small model, handles Hindi, and ignores background noise itself.
  // Chrome/Edge: the browser's own recognizer (Google, free, accurate) behind the same message interface.
  // Not in Telegram (its WebView lacks it) — there the server recognizer is used.
  function browserSpeechBridge() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    // Not inside an Android app WebView ("; wv)"): the API exists there but has no recognizer behind it.
    if (!Recognition || window.Telegram?.WebApp?.initData || /Brave|; wv\)/i.test(navigator.userAgent)) return null;
    let recognition = null;
    const bridge = {
      onmessage: null,
      postMessage(raw) {
        const command = JSON.parse(raw);
        const send = (kind, text = "") => bridge.onmessage?.({ data: JSON.stringify({ kind, text }) });
        if (command.cmd === "stop") { recognition?.abort(); return; }
        recognition?.abort();
        recognition = new Recognition();
        recognition.lang = command.lang || "en-IN";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        let settled = false;
        recognition.onstart = () => send("ready");
        recognition.onspeechstart = () => send("speech");
        recognition.onresult = (event) => { settled = true; send("result", event.results[0][0].transcript); };
        recognition.onerror = (event) => {
          settled = true;
          send(["no-speech", "aborted"].includes(event.error) ? "nomatch"
            : ["not-allowed", "service-not-allowed"].includes(event.error) ? "denied" : "error", event.error);
        };
        recognition.onend = () => { if (!settled) send("nomatch"); };
        try { recognition.start(); } catch { send("error", "start"); }
      },
    };
    return bridge;
  }
  let nativeVoice = window.AtulyaNative && typeof window.AtulyaNative.postMessage === "function"
    ? window.AtulyaNative : browserSpeechBridge();

  if (window.AtulyaNative && !localStorage.getItem("atulya-bg-asked")) {
    localStorage.setItem("atulya-bg-asked", "1");
    window.AtulyaNative.postMessage(JSON.stringify({cmd:"background_connection"}));
  }
  let nativeVoiceErrors = 0;
  if (nativeVoice) {
    nativeVoice.onmessage = async (event) => {
      let message = {};
      try { message = JSON.parse(event.data); } catch { return; }
      if (message.type === "phone_action") { document.dispatchEvent(new CustomEvent("atulya-phone-receipt", {detail:message})); return; }
      if (message.kind === "ready") { setPhase("listening", "Listening", "Speak naturally. I'll answer when you pause."); return; }
      if (message.kind === "speech" || message.kind === "end") return;
      listening = false;
      refreshWave();
      if (!voiceSessionActive) return;
      if (message.kind === "result") {
        nativeVoiceErrors = 0;
        const transcript = applyWakeWord(String(message.text || "").trim());
        if (!transcript) { resumeLiveVoice(); return; } // not addressed to Atulya, or just the name
        await sendMessage(transcript, true, null, "voice");
        if (!speaking) resumeLiveVoice();
        return;
      }
      if (message.kind === "nomatch" || message.kind === "busy") { resumeLiveVoice(); return; } // silence: just listen again
      voiceSessionActive = false;
      if (message.kind === "denied") setPhase("idle", "Allow microphone", "Allow the microphone for Atulya in Android settings, then tap the wave.");
      else if (++nativeVoiceErrors >= 3) {
        if (!window.AtulyaNative) { // browser recognizer unavailable here (offline, blocked): use the server's
          nativeVoice = null;
          const engine = document.getElementById("voice-engine");
          if (engine) engine.textContent = darija("VOICE: SERVER RECOGNIZER");
          voiceSessionActive = true;
          startListening(true);
          return;
        }
        setPhase("idle", "Voice paused", "The phone's speech service is not responding. Tap the wave to try again.");
      }
      else { voiceSessionActive = true; resumeLiveVoice(); }
    };
  }

  // Which recognizer this device uses (shown in the ⋮ menu; the emulator test reads it too).
  {
    const engine = document.getElementById("voice-engine");
    if (engine) engine.textContent = darija(window.AtulyaNative ? "VOICE: PHONE RECOGNIZER"
      : nativeVoice ? "VOICE: BROWSER RECOGNIZER" : "VOICE: SERVER RECOGNIZER");
  }

  async function startListening(resume = false) {
    if (!resume) voiceSessionActive = true;
    if (nativeVoice) {
      listening = true;
      setPhase("listening", "Listening", "Speak naturally. I'll answer when you pause.");
      refreshWave();
      nativeVoice.postMessage(JSON.stringify({ cmd: "listen", lang: /^hi/i.test(navigator.language || "") ? "hi-IN" : "en-IN" }));
      return;
    }
    if (!voiceReady) {
      voiceSessionActive = false;
      setPhase("idle", "Voice unavailable", "Local speech input is not ready. Restart Atulya after voice setup completes.");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      voiceSessionActive = false;
      voiceBrowserBlocked = true;
      setPhase("idle", "Voice unavailable", "This browser can't record microphone audio. You can type below.");
      return;
    }
    const AudioContextType = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextType) {
      voiceSessionActive = false;
      voiceBrowserBlocked = true;
      setPhase("idle", "Voice unavailable", "This browser can't measure microphone input. You can type below.");
      return;
    }
    const requestId = ++voiceRequest;
    listening = true;
    speechDetected = false;
    lastSpeechAt = 0;
    noiseFloor = 0.003;
    recorderChunks = [];
    setPhase("listening", "Allow microphone", "Grant microphone access once. Speech sends automatically after each pause.");
    try {
      const reusable = microphoneStream?.getAudioTracks().some((track) => track.readyState === "live");
      if (reusable) microphoneStream.getAudioTracks().forEach((track) => { track.enabled = true; });
      microphoneStream = reusable ? microphoneStream
        : await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      if (requestId !== voiceRequest) {
        microphoneStream.getTracks().forEach((track) => track.stop());
        microphoneStream = undefined;
        return;
      }
      voiceBrowserBlocked = false;
      microphoneContext = new AudioContextType();
      microphoneAnalyser = microphoneContext.createAnalyser();
      microphoneAnalyser.fftSize = 512;
      microphoneContext.createMediaStreamSource(microphoneStream).connect(microphoneAnalyser);
      const mimeCandidates = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"];
      recordingMime = mimeCandidates.find((mime) => MediaRecorder.isTypeSupported?.(mime)) || "";
      recorder = recordingMime ? new MediaRecorder(microphoneStream, { mimeType: recordingMime }) : new MediaRecorder(microphoneStream);
      recordingMime = recorder.mimeType || recordingMime || "audio/webm";
      recorder.ondataavailable = (event) => { if (event.data?.size) recorderChunks.push(event.data); };
      recorder.onerror = () => {
        cancelListening().then(() => {
          const message = "The browser stopped recording. Check microphone access or type below.";
          setPhase("idle", "Microphone error", message);
          appendMessage("notice", message);
        });
      };
      recorder.start(200);
      const waiting = wakeWordEnabled && Date.now() >= awakeUntil;
      setPhase("listening", waiting ? "Say “Hey Atulya”" : "Listening",
        waiting ? "Live voice is on. Start with “Hey Atulya”; talk over me to interrupt."
          : "Speak naturally. Each turn sends after a pause; Atulya then listens again.");
      refreshWave();
    } catch (error) {
      if (requestId !== voiceRequest) return;
      await releaseMicrophone();
      listening = false;
      voiceSessionActive = false;
      voiceBrowserBlocked = true;
      const errors = {
        NotAllowedError: "Microphone permission was denied. Allow microphone access in browser settings, or type below.",
        PermissionDeniedError: "Microphone permission was denied. Allow microphone access in browser settings, or type below.",
        NotFoundError: "No microphone was found. Connect a microphone or type below.",
        NotReadableError: "The microphone is busy or unavailable. Close other apps using it, or type below.",
        SecurityError: "Microphone capture requires localhost or a secure HTTPS page.",
      };
      setPhase("idle", "Microphone unavailable", errors[error.name] || error.message || "Allow microphone access or type below.");
    }
  }

  function toggleListening() {
    if (!voiceSessionActive) {
      startListening();
      return;
    }
    const shouldSendFinalSpeech = !nativeVoice && listening && speechDetected && recorder;
    voiceSessionActive = false;
    if (shouldSendFinalSpeech) finishListening();
    else cancelListening("Live voice stopped.");
  }

  waveform.addEventListener("click", toggleListening);
  cameraToggle?.addEventListener("click", toggleCamera);
  function syncGestureButton() {
    const button = $("#quick-gesture");
    if (!button) return;
    const active = gesturesEnabled && cameraStream && gestureModelReady;
    const status = !gesturesEnabled ? "red" : (active ? "green" : "yellow");
    button.setAttribute("aria-pressed", String(gesturesEnabled));
    button.dataset.status = status;
    const pip = button.querySelector(".status-pip");
    if (pip) pip.className = `status-pip ${status}`;
    button.title = darija(!gesturesEnabled ? "Gestures: Inactive · Click to turn on" :
      (active ? "Gestures: Active & Scanning · Click to turn off" : "Gestures: Standby (Waiting for camera) · Click to turn off"));
  }

  function syncCameraButton(starting = false) {
    const button = $("#quick-camera");
    if (!button) return;
    const active = Boolean(cameraStream);
    const status = starting ? "yellow" : (active ? "green" : "red");
    button.setAttribute("aria-pressed", String(active));
    button.dataset.status = status;
    const pip = button.querySelector(".status-pip");
    if (pip) pip.className = `status-pip ${status}`;
    button.title = darija(starting ? "Camera: Starting…" :
      (active ? "Camera: Live · Click to turn off" : "Camera: Inactive · Click to turn on"));
  }

  $("#quick-gesture")?.addEventListener("click", async () => {
    gesturesEnabled = !gesturesEnabled;
    syncGestureButton();
    if (!gesturesEnabled) {
      if (gestureFrame) cancelAnimationFrame(gestureFrame);
      gestureFrame = 0;
      gestureRecognizer?.close?.(); gestureRecognizer = undefined; gestureModelReady = false;
      showGestureResult("OFF"); setSystemTile("gesture", "off", "Gestures off");
    } else {
      if (cameraStream) await initializeGestureRecognition();
      else await enableCamera();
    }
    syncGestureButton();
  });
  $("#quick-camera")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    syncCameraButton(true);
    try { await toggleCamera(); }
    finally {
      button.disabled = false;
      syncCameraButton(false);
      syncGestureButton();
    }
  });
  cameraDevice?.addEventListener("click", (event) => event.stopPropagation());
  cameraDevice?.addEventListener("change", async () => {
    selectedCameraDeviceId = cameraDevice.value;
    try { localStorage.setItem("atulya.camera.deviceId", selectedCameraDeviceId); } catch { /* Ignore unavailable storage. */ }
    stopCamera();
    await startCamera();
  });
  waveform.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleListening();
    }
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && (document.body.classList.contains("camera-focus") || document.body.classList.contains("status-focus"))) {
      exitFocusedLayout();
      return;
    }
    if (event.altKey && event.key.toLowerCase() === "m") {
      event.preventDefault();
      toggleListening();
    }
    if (event.key === "Escape" && voiceSessionActive) cancelListening("Live voice stopped.");
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (listening) {
      const typedText = prompt.value.trim();
      if (typedText) {
        cancelListening();
        sendMessage(typedText, voiceReplies);
      }
    } else sendMessage(prompt.value, voiceReplies);
  });
  window.addEventListener("resize", () => { resizeWave(); refreshWave(); });
  window.addEventListener("pagehide", () => { stopCamera(); cameraBus?.close(); }, { once: true });
  resizeWave();
  refreshWave();

  // A6: phones without WebGL (or a scene that never starts) get the hologram artwork as a still image.
  (function hologramFallback() {
    const webgl = (() => { try { const c = document.createElement("canvas"); return Boolean(c.getContext("webgl2") || c.getContext("webgl")); } catch { return false; } })();
    const useFallback = () => {
      if (sceneReady || document.body.classList.contains("scene-fallback")) return;
      document.body.classList.add("scene-fallback");
      window.__HUM_SCENE_READY = true;
      window.dispatchEvent(new Event("atulya:scene-ready"));
    };
    // Slow but working devices keep the live scene: only fall back if no canvas was ever created.
    if (!webgl) useFallback();
    else window.setTimeout(() => { if (!document.querySelector("#root canvas")) useFallback(); }, 8000);
  })();

  window.addEventListener("atulya:scene-ready", () => {
    sceneReady = true;
    greet();
  }, { once: true });
  if (window.__HUM_SCENE_READY) {
    sceneReady = true;
    queueMicrotask(greet);
  }

  function decodeBase64Url(value) {
    const binary = atob(String(value).replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "="));
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
  }

  function encodeBase64Url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  function decodePublicKey(options) {
    const publicKey = { ...options };
    publicKey.challenge = decodeBase64Url(options.challenge);
    if (options.user?.id) publicKey.user = { ...options.user, id: decodeBase64Url(options.user.id) };
    for (const key of ["excludeCredentials", "allowCredentials"]) {
      if (Array.isArray(options[key])) publicKey[key] = options[key].map((item) => ({ ...item, id: decodeBase64Url(item.id) }));
    }
    return publicKey;
  }

  function serializeCredential(credential) {
    const response = credential.response;
    const serialized = {
      id: credential.id,
      rawId: encodeBase64Url(credential.rawId),
      type: credential.type,
      authenticatorAttachment: credential.authenticatorAttachment,
      clientExtensionResults: credential.getClientExtensionResults?.() || {},
      response: { clientDataJSON: encodeBase64Url(response.clientDataJSON) },
    };
    if (response.attestationObject) serialized.response.attestationObject = encodeBase64Url(response.attestationObject);
    if (response.authenticatorData) serialized.response.authenticatorData = encodeBase64Url(response.authenticatorData);
    if (response.signature) serialized.response.signature = encodeBase64Url(response.signature);
    if (response.userHandle) serialized.response.userHandle = encodeBase64Url(response.userHandle);
    if (response.getTransports) serialized.response.transports = response.getTransports();
    return serialized;
  }

  async function startAuthorizedApplication() {
    if (applicationStarted) return;
    applicationStarted = true;
    fetch("/api/health", { headers: { Accept: "application/json" }, cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((health) => {
        voiceReady = Boolean(health.voice_ready && navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
        localTtsReady = Boolean(health.speech_ready);
        brainReady = Boolean(health.brain_configured);
        visionReady = Boolean(health.vision_ready);
        const name = health.assistant_name || "Atulya";
        healthLoaded = true;
        if (connectionDot) connectionDot.setAttribute("aria-label", darija("Atulya service online"));
        if (!brainReady) {
          setPhase("idle", "Chat unavailable", "Text chat is offline right now. The scene remains available.");
        } else if (!voiceReady) {
          setPhase("idle", "Voice unavailable", "Text chat is ready. Voice input and speech are currently offline.");
        } else {
          setPhase("idle", "Ready", `Connected to ${name}. Type or allow microphone access to start voice automatically.`);
        }
        prompt.disabled = !brainReady;
        prompt.placeholder = brainReady ? "Type a message…" : "Chat is starting or unavailable";
        if (visionChannel) setChannelState(visionChannel, "off");
        // Camera on demand only (button, "turn on camera", or a question that needs vision).
        let cameraWanted = false;
        try { cameraWanted = localStorage.getItem("atulya.camera.on") === "1"; } catch { /* ignore */ }
        if (cameraWanted) void startCamera();
        return restoreConversation().then(greet);
      })
      .catch(() => {
        if (connectionDot) connectionDot.classList.add("offline");
        setPhase("idle", "Service unavailable", "Atulya could not be reached. Restart the app and try again.");
      });
    refreshSystemStatus();
    window.setInterval(() => {
      if (document.visibilityState === "visible") refreshSystemStatus();
    }, 3000); // live CPU/RAM/network meters
  }

  // Inside the Telegram Mini App, sign in with Telegram's signed identity (passkeys don't work there).
  let telegramTried = false;
  async function telegramMiniAppSignIn() {
    const webApp = window.Telegram?.WebApp;
    if (telegramTried || !webApp?.initData) return false;
    telegramTried = true;
    webApp.ready?.();
    webApp.expand?.();
    try {
      const response = await fetch("/api/auth/telegram-webapp", {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ init_data: webApp.initData }), cache: "no-store",
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok && authMessage) authMessage.textContent = darija(body.detail || "Telegram sign-in failed.");
      return response.ok;
    } catch { return false; }
  }

  async function refreshAuthState() {
    await telegramMiniAppSignIn();
    try {
      const response = await fetch("/api/auth/status", { headers: { Accept: "application/json" }, cache: "no-store" });
      if (!response.ok) throw new Error("Atulya could not check the local session.");
      const auth = await response.json();
      authSetupRequired = Boolean(auth.setup_required);
      if (authSetupTokenWrap) authSetupTokenWrap.hidden = !auth.setup_token_required || !auth.setup_token_configured;
      if (auth.authenticated) {
        if (authDialog.open) authDialog.close();
        document.body.classList.remove("auth-required");
        if (addPasskeyButton) addPasskeyButton.hidden = false;
        startLiveSync();
        void loadNickname();
        window.setTimeout(enablePushNotifications, 4000);
        if (document.getElementById("add-voice-unlock")) document.getElementById("add-voice-unlock").hidden = false;
        if (manageUsersButton) manageUsersButton.hidden = !auth.is_admin;
        document.body.classList.toggle("non-admin", !auth.is_admin);
        if (signOutButton) signOutButton.hidden = false;
        startAuthorizedApplication();
        return;
      }
      if (cameraStream) stopCamera();
      document.body.classList.add("auth-required");
      if (addPasskeyButton) addPasskeyButton.hidden = true;
      if (manageUsersButton) manageUsersButton.hidden = true;
      if (signOutButton) signOutButton.hidden = true;
      if (authMessage) authMessage.textContent = darija(auth.setup_token_required && !auth.setup_token_configured
        ? "Remote first-time setup is locked. Configure ATULYA_ADMIN_SETUP_TOKEN on the server, then reload this page."
        : authSetupRequired
        ? "Create the first administrator passkey to protect Atulya on this device."
        : "Sign in with your fingerprint, face or screen lock, or with your username.");
      if (authActivate) authActivate.textContent = darija(authSetupRequired ? "CREATE ADMIN PASSKEY" : deviceLinkToken ? "ADD PASSKEY FOR THIS DEVICE" : "SIGN IN WITH PASSKEY");
      const voiceButton = document.getElementById("auth-voice-unlock");
      if (voiceButton) {
        let hasKey = false;
        try { hasKey = Boolean(localStorage.getItem("atulya.voiceUnlock")); } catch { /* storage blocked */ }
        voiceButton.hidden = !hasKey;
      }
      const usePassword = document.getElementById("auth-use-password");
      if (usePassword) usePassword.hidden = !auth.password_login;
      if (!authDialog.open) authDialog.showModal();
    } catch (error) {
      document.body.classList.add("auth-required");
      if (authMessage) authMessage.textContent = darija(error.message) || "Atulya could not check sign-in status.";
      if (!authDialog.open) authDialog.showModal();
    }
  }

  // "#link=<token>" (from LINK A DEVICE) adds a passkey for an existing account on this device/address.
  let deviceLinkToken = "";
  {
    const match = location.hash.match(/(?:^#|&)link=([A-Za-z0-9_-]{16,128})/);
    if (match) {
      deviceLinkToken = match[1];
      history.replaceState(null, "", location.pathname + location.search);
    }
  }

  async function runPasskeyCeremony(kind) {
    if (!window.PublicKeyCredential || !navigator.credentials) {
      throw new Error("This browser does not support device passkeys. Update the browser or use a passkey-capable browser.");
    }
    const isRegistration = kind === "register" || kind === "invite";
    const setupToken = authSetupToken?.value.trim() || "";
    const inviteToken = kind === "invite" ? authInviteToken?.value.trim() || "" : "";
    const authHeaders = { Accept: "application/json" };
    if (isRegistration && setupToken) authHeaders["X-Atulya-Setup-Token"] = setupToken;
    if (inviteToken) authHeaders["X-Atulya-Invite-Token"] = inviteToken;
    if (isRegistration && deviceLinkToken) authHeaders["X-Atulya-Device-Token"] = deviceLinkToken;
    const optionsResponse = await fetch(`/api/auth/${isRegistration ? "register" : "login"}/options`, {
      method: "POST", headers: authHeaders, cache: "no-store",
    });
    const optionsBody = await optionsResponse.json().catch(() => ({}));
    if (!optionsResponse.ok) throw new Error(optionsBody.detail || "Passkey setup could not start.");
    let credential;
    try {
      credential = isRegistration
        ? await navigator.credentials.create({ publicKey: decodePublicKey(optionsBody.options) })
        : await navigator.credentials.get({ publicKey: decodePublicKey(optionsBody.options) });
    } catch (error) {
      const reasons = {
        InvalidStateError: "This device already has a passkey for this account. Use SIGN IN WITH PASSKEY instead.",
        NotAllowedError: "The passkey prompt was cancelled or timed out. Try again and confirm with your fingerprint, face or PIN.",
        SecurityError: "Passkeys only work at https://atulya.atulvij.com. Open Atulya from that address.",
        NotSupportedError: "This device has no passkey provider. On Android, turn on Google Password Manager (Settings → Passwords).",
      };
      throw new Error(reasons[error.name] || `Passkey failed (${error.name || "error"}): ${error.message || "unknown"}`);
    }
    if (!credential) throw new Error("The passkey operation was cancelled.");
    const verifyResponse = await fetch(`/api/auth/${isRegistration ? "register" : "login"}/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json", Accept: "application/json",
        ...(isRegistration && setupToken ? { "X-Atulya-Setup-Token": setupToken } : {}),
        ...(inviteToken ? { "X-Atulya-Invite-Token": inviteToken } : {}),
        ...(isRegistration && deviceLinkToken ? { "X-Atulya-Device-Token": deviceLinkToken } : {}),
      },
      body: JSON.stringify({ flow_id: optionsBody.flow_id, credential: serializeCredential(credential) }),
      cache: "no-store",
    });
    const verifyBody = await verifyResponse.json().catch(() => ({}));
    if (!verifyResponse.ok) throw new Error(verifyBody.detail || "Passkey verification failed.");
    return verifyBody;
  }


  // ---- Sign in with a code (Telegram / email / approval on a signed-in device) ----
  let loginRequestId = "";
  let loginPoll = 0;
  const codeBox = document.getElementById("auth-code");
  const codeStatus = document.getElementById("auth-code-status");
  const codeInput = document.getElementById("auth-code-input");

  async function finishCodeLogin(response) {
    const body = await response.json().catch(() => ({}));
    if (body.authenticated) {
      try { sessionStorage.removeItem("atulya.loginRequest"); } catch { /* ignore */ }
      offerPasskeyAfterSignIn();
      window.clearInterval(loginPoll);
      loginRequestId = "";
      authDialog.close();
      document.body.classList.remove("auth-required");
      await refreshAuthState();
      return true;
    }
    if (body.state === "denied" || body.state === "expired") {
      window.clearInterval(loginPoll);
      codeStatus.textContent = darija(body.state === "denied" ? "Sign-in was denied or locked. Start again." : "The code expired. Start again.");
    }
    return false;
  }

  // Coming back (app switched to Telegram and back, or page reloaded): keep the same pending code.
  function resumePendingLogin() {
    let saved = null;
    try { saved = JSON.parse(sessionStorage.getItem("atulya.loginRequest") || "null"); } catch { /* ignore */ }
    if (!saved?.id || Date.now() - saved.at > 5 * 60 * 1000 || !codeBox) return;
    loginRequestId = saved.id;
    codeBox.hidden = false;
    codeStatus.textContent = darija("Enter the code from Telegram, or approve on a signed-in device.");
    window.clearInterval(loginPoll);
    loginPoll = window.setInterval(async () => {
      if (!loginRequestId) return;
      await finishCodeLogin(await fetch(`/api/auth/login-requests/${encodeURIComponent(loginRequestId)}`, { cache: "no-store" }));
    }, 2000);
  }

  // "Tap to sign in" link from Telegram/email: #signin=<request>.<code>
  async function signInFromLink() {
    const match = location.hash.match(/signin=([A-Za-z0-9_-]{10,40})\.(\d{6})/);
    if (!match) return false;
    history.replaceState(null, "", location.pathname + location.search);
    const response = await fetch(`/api/auth/login-requests/${encodeURIComponent(match[1])}/code`, {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ code: match[2] }), cache: "no-store",
    });
    return finishCodeLogin(response);
  }
  window.setTimeout(() => { signInFromLink().then((done) => { if (!done) resumePendingLogin(); }); }, 300);

  // Google-style steps: start (passkey / identify) -> methods for that account.
  function showAuthStep(step) {
    document.getElementById("auth-step-start").hidden = step !== "start";
    document.getElementById("auth-step-methods").hidden = step !== "methods";
    document.getElementById("auth-signup-form").hidden = step !== "signup";
    const title = document.getElementById("auth-title");
    if (title && !authSetupRequired) title.textContent = darija(step === "signup" ? "CREATE YOUR ACCOUNT" : "SIGN IN TO ATULYA");
    const subtitle = document.getElementById("auth-message");
    if (subtitle && !authSetupRequired && step === "signup") subtitle.textContent = darija("Your account is ready once the owner approves it.");
  }
  document.getElementById("auth-identify")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const who = document.getElementById("auth-username").value.trim();
    if (!who) return;
    document.getElementById("auth-who").textContent = who;
    document.getElementById("auth-password-form").hidden = true;
    codeBox.hidden = true;
    showAuthStep("methods");
    if (authMessage) authMessage.textContent = darija("Choose how to confirm it's you.");
  });
  document.getElementById("auth-change-user")?.addEventListener("click", () => showAuthStep("start"));
  document.getElementById("auth-use-password")?.addEventListener("click", () => {
    document.getElementById("auth-password-form").hidden = false;
    document.getElementById("auth-password").focus();
  });
  document.getElementById("auth-signup-start")?.addEventListener("click", () => showAuthStep("signup"));
  document.getElementById("auth-signup-back")?.addEventListener("click", () => showAuthStep("start"));
  let lastCodeRequest = 0;
  document.getElementById("auth-code-resend")?.addEventListener("click", () => {
    const wait = 30 - Math.floor((Date.now() - lastCodeRequest) / 1000);
    if (wait > 0) { codeStatus.textContent = darija(`You can resend in ${wait}s.`); return; }
    document.getElementById("auth-code-start").click();
  });

  document.getElementById("auth-code-start")?.addEventListener("click", async () => {
    lastCodeRequest = Date.now();
    codeBox.hidden = false;
    codeStatus.textContent = darija("Sending a code…");
    try {
      const response = await fetch("/api/auth/login-requests", {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ username: document.getElementById("auth-username")?.value || "atulya" }), cache: "no-store",
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not start sign-in.");
      loginRequestId = body.id;
      try { sessionStorage.setItem("atulya.loginRequest", JSON.stringify({ id: body.id, at: Date.now() })); } catch { /* ignore */ }
      codeStatus.textContent = darija(`Approve on ${body.channels.join(" or ")} — or type the 6-digit code from Telegram. Expires in 5 minutes.`);
      codeInput.focus();
      window.clearInterval(loginPoll);
      loginPoll = window.setInterval(async () => {
        if (!loginRequestId) return;
        await finishCodeLogin(await fetch(`/api/auth/login-requests/${encodeURIComponent(loginRequestId)}`, { cache: "no-store" }));
      }, 2000);
    } catch (error) {
      codeStatus.textContent = darija(error.message);
    }
  });

  document.getElementById("auth-code-submit")?.addEventListener("click", async () => {
    if (!loginRequestId) return;
    const ok = await finishCodeLogin(await fetch(`/api/auth/login-requests/${encodeURIComponent(loginRequestId)}/code`, {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ code: codeInput.value }), cache: "no-store",
    }));
    if (!ok) codeStatus.textContent = darija("That code didn't match. Check it and try again.");
  });
  codeInput?.addEventListener("keydown", (event) => { if (event.key === "Enter") document.getElementById("auth-code-submit").click(); });

  // Signed-in devices: show and announce sign-in requests from other devices.
  const shownLoginRequests = new Set();
  async function checkPendingLogins() {
    if (document.body.classList.contains("auth-required")) return;
    try {
      const response = await fetch("/api/auth/pending-logins", { headers: { Accept: "application/json" }, cache: "no-store" });
      if (!response.ok) return;
      for (const item of (await response.json()).requests || []) {
        if (shownLoginRequests.has(item.id)) continue;
        shownLoginRequests.add(item.id);
        const card = document.createElement("div");
        card.className = "chat-message action-card";
        card.innerHTML = darija("<strong>SIGN-IN REQUEST</strong><span></span><div><button class=\"approve\" type=\"button\">APPROVE</button><button type=\"button\">DENY</button></div>");
        card.querySelector("span").textContent = darija(`Someone wants to sign in from ${item.label}.`);
        const [approve, deny] = card.querySelectorAll("button");
        const decide = async (yes) => {
          approve.disabled = deny.disabled = true;
          card.dataset.state = yes ? "approved" : "denied";
          await fetch(`/api/auth/pending-logins/${encodeURIComponent(item.id)}`, {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approve: yes }),
          }).catch(() => {});
        };
        approve.addEventListener("click", () => decide(true));
        deny.addEventListener("click", () => decide(false));
        messagesNode.append(card);
        messagesNode.scrollTop = messagesNode.scrollHeight;
        if (!speaking) speak(`Someone is asking to sign in from ${item.label}. Approve only if it's you.`);
      }
    } catch { /* offline; try again next tick */ }
  }
  window.setInterval(checkPendingLogins, 3000);


  // ---- Voice unlock (trusted device + spoken phrase) -------------------------------
  const VOICE_KEY = "atulya.voiceUnlock";
  const readVoiceKey = () => { try { return JSON.parse(localStorage.getItem(VOICE_KEY) || "null"); } catch { return null; } };
  const voiceUnlockButton = document.getElementById("auth-voice-unlock");
  const addVoiceUnlockButton = document.getElementById("add-voice-unlock");

  async function recordSeconds(seconds) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    const chunks = [];
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (event) => { if (event.data?.size) chunks.push(event.data); };
    recorder.start();
    await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
    await new Promise((resolve) => { recorder.onstop = resolve; recorder.stop(); });
    stream.getTracks().forEach((track) => track.stop());
    return new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
  }

  addVoiceUnlockButton?.addEventListener("click", async () => {
    const phrase = window.prompt("Choose a private unlock phrase (3+ words) you'll say to unlock THIS device, e.g. 'saffron rocket at midnight'. Don't use your password.");
    if (!phrase) return;
    const response = await fetch("/api/auth/voice-unlock/enroll", {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ phrase }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) { appendMessage("notice", body.detail || "Voice unlock could not be set up."); return; }
    try { localStorage.setItem(VOICE_KEY, JSON.stringify({ id: body.id, secret: body.device_secret })); } catch { /* storage blocked */ }
    appendMessage("assistant", "Voice unlock is set up on this device. Next time, tap UNLOCK WITH VOICE and say your phrase.");
  });

  voiceUnlockButton?.addEventListener("click", async () => {
    const key = readVoiceKey();
    if (!key) return;
    voiceUnlockButton.disabled = true;
    voiceUnlockButton.textContent = darija("LISTENING… SAY YOUR PHRASE");
    try {
      const form = new FormData();
      form.append("unlock_id", key.id);
      form.append("device_secret", key.secret);
      form.append("audio", await recordSeconds(4), "phrase.webm");
      voiceUnlockButton.textContent = darija("CHECKING…");
      const response = await fetch("/api/auth/voice-unlock", { method: "POST", body: form });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "That didn't unlock.");
      authDialog.close();
      document.body.classList.remove("auth-required");
      await refreshAuthState();
    } catch (error) {
      if (authMessage) authMessage.textContent = darija(error.message) || "Microphone unavailable here.";
    } finally {
      voiceUnlockButton.disabled = false;
      voiceUnlockButton.textContent = darija("UNLOCK WITH VOICE");
    }
  });

  document.getElementById("auth-password-toggle")?.addEventListener("click", (event) => {
    const field = document.getElementById("auth-password");
    const show = field.type === "password";
    field.type = show ? "text" : "password";
    event.currentTarget.setAttribute("aria-pressed", String(show));
    event.currentTarget.setAttribute("aria-label", darija(show ? "Hide password" : "Show password"));
    event.currentTarget.textContent = show ? "🙈" : "👁";
    field.focus();
  });

  document.getElementById("auth-password-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = document.getElementById("auth-password");
    try {
      const response = await fetch("/api/auth/password", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ username: document.getElementById("auth-username").value, password: password.value }),
        cache: "no-store",
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Sign-in failed.");
      password.value = "";
      offerPasskeyAfterSignIn();
      authDialog.close();
      document.body.classList.remove("auth-required");
      await refreshAuthState();
    } catch (error) {
      if (authMessage) authMessage.textContent = darija(error.message);
    }
  });

  authActivate?.addEventListener("click", async () => {
    authActivate.disabled = true;
    try {
      if (authMessage) authMessage.textContent = darija(authSetupRequired ? "Follow your device prompt to create the admin passkey." : "Confirm with your device passkey.");
      await runPasskeyCeremony(authSetupRequired || deviceLinkToken ? "register" : "login");
      try { localStorage.setItem("atulya.passkeyHere", "1"); } catch { /* ignore */ }
      deviceLinkToken = "";
      if (authSetupToken) authSetupToken.value = "";
      await refreshAuthState();
    } catch (error) {
      if (authMessage) authMessage.textContent = darija(error.message) || "Passkey sign-in failed. Try again.";
    } finally {
      authActivate.disabled = false;
    }
  });

  authJoin?.addEventListener("click", async () => {
    authJoin.disabled = true;
    try {
      if (authMessage) authMessage.textContent = darija("Follow your device prompt to create your private passkey.");
      await runPasskeyCeremony("invite");
      if (authInviteToken) authInviteToken.value = "";
      await refreshAuthState();
    } catch (error) {
      if (authMessage) authMessage.textContent = darija(error.message) || "Invitation enrollment failed. Check the code and try again.";
    } finally {
      authJoin.disabled = false;
    }
  });

  // After a password/code sign-in on a device without a passkey, offer one tap to add it.
  function offerPasskeyAfterSignIn() {
    let known = false;
    try { known = localStorage.getItem("atulya.passkeyHere") === "1"; } catch { /* ignore */ }
    if (known || !window.PublicKeyCredential || !navigator.credentials) return;
    window.setTimeout(() => {
      const card = document.createElement("div");
      card.className = "chat-message action-card";
      card.innerHTML = darija("<strong>ADD A PASSKEY?</strong><span>Next time, unlock this device with your fingerprint, face or PIN instead of a password or code.</span><div><button class=\"approve\" type=\"button\">ADD PASSKEY</button><button type=\"button\">NOT NOW</button></div>");
      const [add, later] = card.querySelectorAll("button");
      add.addEventListener("click", async () => {
        add.disabled = later.disabled = true;
        try {
          await runPasskeyCeremony("register");
          try { localStorage.setItem("atulya.passkeyHere", "1"); } catch { /* ignore */ }
          card.dataset.state = "approved";
          card.querySelector("span").textContent = darija("Passkey added. This device now signs in with one touch.");
        } catch (error) {
          card.querySelector("span").textContent = darija(error.message || "Passkey not added. Try again from the menu (PASSKEY +).");
          add.disabled = later.disabled = false;
        }
      });
      later.addEventListener("click", () => card.remove());
      messagesNode.append(card);
      messagesNode.scrollTop = messagesNode.scrollHeight;
    }, 1500);
  }

  addPasskeyButton?.addEventListener("click", async () => {
    addPasskeyButton.disabled = true;
    try {
      await runPasskeyCeremony("register");
      try { localStorage.setItem("atulya.passkeyHere", "1"); } catch { /* ignore */ }
      setPhase("idle", "Backup passkey added", "This device can now use another passkey to unlock Atulya.");
    } catch (error) {
      setPhase("idle", "Passkey not added", error.message || "Try again or use a different passkey device.");
    } finally {
      addPasskeyButton.disabled = false;
    }
  });

  $("#reload-app")?.addEventListener("click", () => window.location.reload());

  // Phone hologram framing: close-up (fills the area) or wide (whole scene, as on the website).
  const sceneViewButton = $("#scene-view");
  function applySceneView(wide) {
    document.body.classList.toggle("scene-wide", wide);
    if (sceneViewButton) sceneViewButton.textContent = darija(wide ? "VIEW: WIDE" : "VIEW: CLOSE-UP");
    window.dispatchEvent(new Event("resize")); // the scene re-measures its box
  }
  applySceneView(readFlag("atulya.scene.wide", false));
  sceneViewButton?.addEventListener("click", () => {
    const wide = !document.body.classList.contains("scene-wide");
    try { localStorage.setItem("atulya.scene.wide", wide ? "1" : "0"); } catch { /* ignore */ }
    applySceneView(wide);
  });

  signOutButton?.addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST", headers: { Accept: "application/json" } }).catch(() => {});
    window.location.reload();
  });

  function appendUserAction(parent, label, action, danger = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = darija(label);
    if (danger) button.dataset.danger = "true";
    button.addEventListener("click", action);
    parent.append(button);
  }


  // ---- Push notifications (sign-in requests, approvals) -------------------------------
  async function enablePushNotifications() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return;
    if (Notification.permission === "denied") return;
    try {
      const registration = await navigator.serviceWorker.ready;
      const { key } = await (await fetch("/api/push/key")).json();
      if (!key) return;
      if (Notification.permission !== "granted" && (await Notification.requestPermission()) !== "granted") return;
      const raw = atob(key.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(key.length / 4) * 4, "="));
      const subscription = (await registration.pushManager.getSubscription()) || await registration.pushManager.subscribe({
        userVisibleOnly: true, applicationServerKey: Uint8Array.from(raw, (c) => c.charCodeAt(0)) });
      await fetch("/api/push/subscribe", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(subscription.toJSON()) });
    } catch { /* notifications are optional */ }
  }

  document.getElementById("auth-google")?.addEventListener("click", (event) => {
    if (window.AtulyaNative) {
      event.preventDefault();
      window.AtulyaNative.postMessage(JSON.stringify({cmd:"google_login",url:new URL("/api/auth/google/start",location.origin).href}));
    }
  });

  // ---- Sign up / Google ------------------------------------------------------------
  const signupForm = document.getElementById("auth-signup-form");

  document.querySelectorAll(".password-eye").forEach((eye) => eye.addEventListener("click", () => {
    const field = eye.previousElementSibling;
    field.type = field.type === "password" ? "text" : "password";
    eye.textContent = field.type === "password" ? "👁" : "🙈";
  }));
  document.getElementById("signup-password")?.addEventListener("input", (event) => {
    const value = event.target.value;
    const kinds = [/[a-z]/, /[A-Z]/, /\d/, /[^\w]/].filter((pattern) => pattern.test(value)).length;
    const hint = document.getElementById("signup-strength");
    hint.textContent = darija(value.length < 10 ? `Too short (${value.length}/10)` : kinds < 3 ? "Add another kind: uppercase, number or symbol" : "Strong password ✓");
    hint.dataset.ok = String(value.length >= 10 && kinds >= 3);
  });
  signupForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/api/auth/signup", {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ name: document.getElementById("signup-name").value,
        email: document.getElementById("signup-email").value, password: document.getElementById("signup-password").value }),
    });
    const body = await response.json().catch(() => ({}));
    const email = document.getElementById("signup-email").value.trim();
    if (!response.ok && /already/i.test(body.detail || "")) {
      // Existing account: go straight to signing in with it.
      document.getElementById("auth-username").value = email;
      document.getElementById("auth-who").textContent = email;
      showAuthStep("methods");
      if (authMessage) authMessage.textContent = darija("You already have an account. Confirm it's you to sign in.");
      return;
    }
    if (authMessage) authMessage.textContent = darija(response.ok
      ? "Account created. It becomes active as soon as it's verified."
      : (body.detail || "Sign-up failed."));
    if (response.ok) { signupForm.reset(); showAuthStep("start"); }
  });
  fetch("/api/auth/options").then((r) => r.json()).then((options) => {
    const google = document.getElementById("auth-google");
    if (google) google.hidden = !options.google;
  }).catch(() => {});
  {
    const result = location.hash.match(/google=(ok|pending|failed|expired)/)?.[1];
    if (result) {
      history.replaceState(null, "", location.pathname + location.search);
      if (result !== "ok" && authMessage) authMessage.textContent = darija({
        pending: "Your Google account is waiting for the owner's approval.",
        failed: "Google sign-in failed. Try again or use another way.",
        expired: "Google sign-in took too long. Try again.",
      }[result]);
    }
  }

  async function drawPendingSignups() {
    const list = document.getElementById("signups-list");
    if (!list) return;
    list.replaceChildren();
    const response = await fetch("/api/auth/signups", { headers: { Accept: "application/json" } }).catch(() => null);
    if (!response?.ok) return;
    for (const item of (await response.json()).signups || []) {
      const row = document.createElement("div");
      row.className = "user-entry";
      const name = document.createElement("strong");
      name.textContent = darija(`${item.display_name} — waiting for approval`);
      const info = document.createElement("small");
      info.textContent = darija(`${item.email} · via ${item.via}`);
      const approve = document.createElement("button");
      approve.type = "button";
      approve.textContent = darija("APPROVE");
      const deny = document.createElement("button");
      deny.type = "button";
      deny.textContent = darija("DENY");
      deny.dataset.danger = "true";
      const decide = async (yes) => {
        await fetch(`/api/auth/signups/${encodeURIComponent(item.user_id)}`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approve: yes }) });
        await drawPendingSignups();
        await refreshUsers();
      };
      approve.addEventListener("click", () => decide(true));
      deny.addEventListener("click", () => decide(false));
      row.append(name, approve, info, deny);
      list.append(row);
    }
  }

  async function refreshUsers() {
    void drawPendingSignups();
    if (!usersList) return;
    usersList.replaceChildren();
    try {
      const response = await fetch("/api/auth/users", { headers: { Accept: "application/json" }, cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not load local accounts.");
      const credentialsByUser = new Map();
      for (const item of body.credentials || []) {
        const list = credentialsByUser.get(item.user_id) || [];
        list.push(item);
        credentialsByUser.set(item.user_id, list);
      }
      for (const user of body.users || []) {
        const card = document.createElement("section");
        card.className = "user-entry";
        const title = document.createElement("strong");
        title.textContent = darija(`${user.display_name} · ${user.role === "admin" ? "ADMIN" : "USER"}`);
        const detail = document.createElement("small");
        detail.textContent = darija(user.credential_count ? `${user.credential_count} passkey(s)` : "Invitation pending");
        card.append(title, detail);
        for (const credential of credentialsByUser.get(user.id) || []) {
          const row = document.createElement("div");
          row.className = "credential-entry";
          const label = document.createElement("small");
          label.textContent = darija(`Passkey · ${new Date(credential.created_at * 1000).toLocaleDateString()}`);
          row.append(label);
          appendUserAction(row, "REVOKE", async () => {
            const result = await fetch(`/api/auth/credentials/${encodeURIComponent(credential.credential_id)}`, { method: "DELETE" });
            if (!result.ok) {
              const data = await result.json().catch(() => ({}));
              setPhase("idle", "Passkey retained", data.detail || "Keep another passkey enrolled first.");
            } else if (credential.user_id === "admin") {
              window.location.reload();
              return;
            }
            await refreshUsers();
          }, true);
          card.append(row);
        }
        if (user.role !== "admin") {
          // PLAN M12-4/M12-6: today's usage against limits, and the server-decided age group.
          const usage = user.usage_today || {};
          const limits = user.limits || {};
          const settings = document.createElement("small");
          settings.className = "user-settings";
          settings.textContent = darija(`Today: ${usage.messages || 0}/${limits.messages_per_day ?? "∞"} messages · ${usage.tools || 0}/${limits.tools_per_day ?? "∞"} tool calls · Age: ${user.age_group} (${user.age_source})${user.notify_blocked ? " · alerts on" : ""}`);
          card.append(settings);
          const send = async (path, payload, failure) => {
            const result = await fetch(path, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
            if (!result.ok) {
              const data = await result.json().catch(() => ({}));
              setPhase("idle", failure, typeof data.detail === "string" ? data.detail : "Check the values and try again.");
            }
            await refreshUsers();
          };
          appendUserAction(card, "SET LIMITS", async () => {
            const messages = window.prompt(`Messages per day for ${user.display_name} (blank = default):`, limits.messages_per_day ?? "");
            if (messages === null) return;
            const tools = window.prompt(`Tool calls per day for ${user.display_name} (blank = default):`, limits.tools_per_day ?? "");
            if (tools === null) return;
            const value = (text) => (String(text).trim() === "" ? null : Number.parseInt(text, 10));
            await send(`/api/auth/users/${encodeURIComponent(user.id)}/limits`,
              { messages_per_day: value(messages), tools_per_day: value(tools) }, "Limits not changed");
          });
          const nextAge = { auto: "adult", adult: "child", child: null };
          const currentAge = user.age_source === "admin" ? user.age_group : "auto";
          appendUserAction(card, `AGE: ${currentAge.toUpperCase()}`, async () => {
            const target = nextAge[currentAge];
            if (!window.confirm(`Set ${user.display_name}'s age group to ${target ?? "automatic (date of birth)"}?`)) return;
            await send(`/api/auth/users/${encodeURIComponent(user.id)}/content`, { age_group: target }, "Age group not changed");
          });
          appendUserAction(card, user.notify_blocked ? "ALERTS: ON" : "ALERTS: OFF", async () => {
            await send(`/api/auth/users/${encodeURIComponent(user.id)}/content`, { notify_blocked: !user.notify_blocked }, "Alert setting not changed");
          });
          appendUserAction(card, "DISABLE USER", async () => {
            if (!window.confirm(`Disable ${user.display_name}? Their passkeys and sessions will be revoked. Saved records will remain on this device.`)) return;
            const result = await fetch(`/api/auth/users/${encodeURIComponent(user.id)}`, { method: "DELETE" });
            if (!result.ok) {
              const data = await result.json().catch(() => ({}));
              setPhase("idle", "User not disabled", data.detail || "Try again.");
            }
            await refreshUsers();
          }, true);
        }
        usersList.append(card);
      }
    } catch (error) {
      const message = document.createElement("p");
      message.textContent = darija(error.message || "Local accounts are unavailable.");
      usersList.append(message);
    }
  }

  manageUsersButton?.addEventListener("click", () => {
    if (!usersDialog?.open) usersDialog?.showModal();
    void refreshUsers();
  });
  $("#close-users")?.addEventListener("click", () => usersDialog?.close());
  document.getElementById("link-device")?.addEventListener("click", async () => {
    try {
      const response = await fetch("/api/auth/device-link", { method: "POST", headers: { Accept: "application/json" } });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not create a device link.");
      const linkDialog = document.createElement("dialog");
      linkDialog.className = "device-link-dialog";
      const inviteResult = document.createElement("div");
      linkDialog.append(inviteResult);
      const close = document.createElement("button"); close.textContent = darija("Close");
      close.addEventListener("click", () => linkDialog.close()); linkDialog.append(close);
      linkDialog.addEventListener("close", () => linkDialog.remove());
      document.body.append(linkDialog); linkDialog.showModal();
      const label = document.createElement("span");
      label.textContent = darija(`Open this on your phone or other computer within ${body.expires_minutes} minutes to add a passkey for your account:`);
      const code = document.createElement("code");
      code.textContent = body.url;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.textContent = darija("COPY LINK");
      copy.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(body.url); copy.textContent = darija("COPIED"); }
        catch { copy.textContent = darija("SELECT LINK TO COPY"); }
      });
      inviteResult.append(label, code, copy);
    } catch (error) {
      setPhase("idle", "Device link not created", error.message || "Try again.");
    }
  });

  inviteUserForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = inviteUserForm.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const response = await fetch("/api/auth/users", {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ display_name: inviteDisplayName.value }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Could not create an invitation.");
      inviteResult.hidden = false;
      inviteResult.replaceChildren();
      const label = document.createElement("span");
      label.textContent = darija(`Share this one-time code with ${body.display_name} (expires in 24 hours):`);
      const code = document.createElement("code");
      code.textContent = body.invitation_token;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.textContent = darija("COPY CODE");
      copy.addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(body.invitation_token); copy.textContent = darija("COPIED"); }
        catch { copy.textContent = darija("SELECT CODE TO COPY"); }
      });
      inviteResult.append(label, code, copy);
      inviteDisplayName.value = "";
      await refreshUsers();
    } catch (error) {
      setPhase("idle", "Invitation not created", error.message || "Try again.");
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("pair-device")?.addEventListener("click", async () => {
    const name = prompt("Device name (Laptop, Phone, etc.):", "Laptop");
    if (!name) return;
    try {
      const r = await fetch("/api/devices/pair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, abilities: ["ping", "open_url", "list_files", "say"] }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Pairing failed");
      const dlg = document.createElement("dialog");
      dlg.innerHTML = `<h3>${darija("Pairing token for")} ${darija(name)}</h3><pre>${data.token}</pre><p>${darija("On the device run:")}<br>ATULYA_AGENT_TOKEN=${data.token} python -m tools.laptop_agent</p><button>${darija("Close")}</button>`;
      dlg.querySelector("button").addEventListener("click", () => dlg.close());
      document.body.append(dlg);
      dlg.showModal();
    } catch (e) {
      alert(darija("Pairing failed") + ": " + darija(e.message));
    }
  });
  // Every device signed in to this account: what, where, how, last used; sign one or all others out.
  document.getElementById("signed-in-devices")?.addEventListener("click", () => {
    const dialog = document.createElement("dialog");
    dialog.className = "device-link-dialog signed-in-devices";
    const title = document.createElement("h3");
    title.textContent = darija("Signed-in devices");
    const list = document.createElement("div");
    const status = document.createElement("p");
    const others = document.createElement("button");
    others.type = "button";
    others.textContent = darija("SIGN OUT ALL OTHER DEVICES");
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = darija("Close");
    close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => dialog.remove());
    dialog.append(title, list, status, others, close);
    document.body.append(dialog);
    dialog.showModal();
    const when = (seconds) => new Date(seconds * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });

    async function draw() {
      list.replaceChildren();
      status.textContent = darija("Loading…");
      const response = await fetch("/api/auth/sessions", { headers: { Accept: "application/json" }, cache: "no-store" }).catch(() => null);
      if (!response?.ok) { status.textContent = darija("Could not load your sign-ins."); return; }
      const { sessions = [] } = await response.json();
      status.textContent = darija(`${sessions.length} signed in. Sign out anything you don't recognise.`);
      for (const item of sessions) {
        const row = document.createElement("div");
        row.className = "chat-message action-card";
        const name = document.createElement("strong");
        name.textContent = darija(item.current ? `${item.label} · THIS DEVICE` : item.label);
        const detail = document.createElement("span");
        detail.textContent = darija(`${item.method || "sign-in"} · ${item.ip || "unknown network"} · signed in ${when(item.created_at)} · last used ${when(item.last_seen)}`);
        row.append(name, detail);
        if (!item.current) {
          const out = document.createElement("button");
          out.type = "button";
          out.textContent = darija("SIGN OUT");
          out.addEventListener("click", async () => {
            out.disabled = true;
            const done = await fetch(`/api/auth/sessions/${encodeURIComponent(item.id)}`, { method: "DELETE" }).catch(() => null);
            if (done?.ok || done?.status === 404) row.remove(); else out.disabled = false;
          });
          row.append(out);
        }
        list.append(row);
      }
    }

    others.addEventListener("click", async () => {
      if (!confirm(darija("Sign out every other phone, computer and browser? They will need to sign in again."))) return;
      others.disabled = true;
      const response = await fetch("/api/auth/sessions/sign-out-others", { method: "POST" }).catch(() => null);
      const body = response?.ok ? await response.json() : null;
      status.textContent = darija(body ? `Signed out ${body.signed_out} other device(s).` : "Could not sign out other devices.");
      others.disabled = false;
      if (body) void draw();
    });
    void draw();
  });

  void refreshAuthState();
})();
