const $ = (selector) => document.querySelector(selector);
const state = { presets: {}, parameters: {}, selected: 'clean_master', values: {}, upload: null, buffer: null, jobs: [] };
const audio = $('#audio');

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

function toast(message) {
  const element = $('#toast'); element.textContent = message; element.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => element.classList.remove('show'), 2800);
}

function formatTime(seconds = 0) {
  const minutes = Math.floor(seconds / 60); const rest = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${rest.toFixed(1).padStart(4, '0')}`;
}

async function boot() {
  try {
    const [config, health, jobs] = await Promise.all([api('/api/presets'), api('/api/health'), api('/api/jobs')]);
    state.presets = config.presets; state.parameters = config.parameters; state.jobs = jobs.jobs;
    $('#healthDot').style.background = health.ffmpeg ? 'var(--acid)' : 'var(--amber)';
    $('#healthText').textContent = health.ffmpeg ? 'ENGINE ONLINE' : 'FFMPEG MISSING';
    renderPresets(); selectPreset(state.selected); renderJobs();
  } catch (error) { toast(error.message); }
}

function renderPresets(query = '') {
  const list = $('#presetList'); list.innerHTML = ''; let lastCategory = '';
  Object.entries(state.presets).filter(([, p]) => `${p.name} ${p.category}`.toLowerCase().includes(query.toLowerCase())).forEach(([id, preset]) => {
    if (preset.category !== lastCategory) { const label = document.createElement('div'); label.className = 'category'; label.textContent = preset.category.toUpperCase(); list.append(label); lastCategory = preset.category; }
    const button = document.createElement('button'); button.className = `preset ${id === state.selected ? 'active' : ''}`; button.dataset.id = id;
    button.innerHTML = `${preset.name}<small>${preset.category}</small>`; button.onclick = () => selectPreset(id); list.append(button);
  });
}

function selectPreset(id) {
  state.selected = id; state.values = {...state.presets[id].values};
  $('#presetName').textContent = state.presets[id].name; $('#presetDescription').textContent = state.presets[id].description;
  renderPresets($('#presetSearch').value); renderFaders();
}

function renderFaders() {
  const root = $('#faders'); root.innerHTML = '';
  Object.entries(state.parameters).forEach(([key, spec]) => {
    const value = state.values[key]; const normalized = (value - spec.min) / (spec.max - spec.min);
    const node = document.createElement('div'); node.className = 'fader';
    node.innerHTML = `<output class="readout">${displayValue(value, spec)}</output><div class="track"><div class="meter" style="height:${Math.max(3, normalized * 100)}%"></div><input aria-label="${spec.label}" type="range" min="${spec.min}" max="${spec.max}" step="${spec.step}" value="${value}"></div><label>${spec.label.toUpperCase()}</label><small>${spec.unit}</small>`;
    const input = node.querySelector('input'); input.oninput = () => { state.values[key] = Number(input.value); node.querySelector('output').textContent = displayValue(state.values[key], spec); node.querySelector('.meter').style.height = `${Math.max(3, (state.values[key]-spec.min)/(spec.max-spec.min)*100)}%`; };
    root.append(node);
  });
}
function displayValue(value, spec) { return `${value > 0 && spec.unit === 'dB' ? '+' : ''}${Number(value).toFixed(spec.step < 1 ? 1 : 0)}`; }

async function loadFile(file) {
  if (!file?.type.startsWith('audio/') && !/\.(wav|mp3|flac|m4a|aac|ogg|opus|aiff?)$/i.test(file.name)) return toast('Choose a supported audio file');
  $('#sourceName').textContent = `UPLOADING · ${file.name}`; $('#sourceStatus').textContent = 'UPLOADING';
  try {
    const upload = await api('/api/upload', {method:'POST', headers:{'Content-Type':'application/octet-stream','X-Filename':encodeURIComponent(file.name)}, body:file});
    state.upload = upload; audio.src = upload.media_url; $('#sourceName').textContent = file.name; $('#sourceMeta').textContent = `${(file.size/1048576).toFixed(2)} MB · READY TO PROCESS`; $('#sourceStatus').textContent = 'READY'; $('#render').disabled = false;
    const context = new (window.AudioContext || window.webkitAudioContext)(); state.buffer = await context.decodeAudioData(await file.arrayBuffer()); drawWaveform(state.buffer); $('#duration').textContent = `/ ${formatTime(state.buffer.duration)}`;
  } catch(error) { $('#sourceStatus').textContent = 'UPLOAD FAILED'; toast(error.message); }
}

function drawWaveform(buffer) {
  const canvas = $('#waveform'), ratio = window.devicePixelRatio || 1, width = canvas.clientWidth, height = canvas.clientHeight;
  canvas.width = width * ratio; canvas.height = height * ratio; const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); ctx.clearRect(0,0,width,height);
  const data = buffer.getChannelData(0), samples = Math.floor(width / 3), block = Math.max(1, Math.floor(data.length / samples));
  const gradient = ctx.createLinearGradient(0,0,width,0); gradient.addColorStop(0,'#6cc8ff'); gradient.addColorStop(.54,'#d7ff43'); gradient.addColorStop(1,'#ffb547'); ctx.fillStyle = gradient;
  for(let i=0;i<samples;i++){ let min=1,max=-1; for(let j=0;j<block;j++){const v=data[i*block+j]||0;if(v<min)min=v;if(v>max)max=v;} const y=(1+min)*height/2, bar=Math.max(1,(max-min)*height/2); ctx.globalAlpha=.48+Math.min(1,bar/height);ctx.fillRect(i*3,y,1.5,bar); }
  $('#waveEmpty').style.display='none'; $('#playhead').style.display='block';
}

async function renderAudio() {
  if (!state.upload) return; const button=$('#render'); button.disabled=true; button.querySelector('span').textContent='PROCESSING…'; $('#outputStatus').textContent='RENDERING';
  try {
    const extension=$('#format').value, base=state.upload.name.replace(/\.[^.]+$/,'').replace(/[^a-z0-9_-]/gi,'-');
    const request={input:state.upload.path,output:`${base}-${state.selected}.${extension}`,preset:state.selected,parameters:state.values,rights:$('#rights').value,intent:$('#intent').value,actor:'studio-ui',overwrite:true};
    let job=await api('/api/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}); pollJob(job.id);
  } catch(error) { button.disabled=false; button.querySelector('span').textContent='RENDER MASTER'; $('#outputStatus').textContent='FAILED'; toast(error.message); }
}

async function pollJob(id) {
  try {
    const job=await api(`/api/jobs/${id}`); if(['prepared','processing'].includes(job.status)){setTimeout(()=>pollJob(id),700);return;}
    $('#render').disabled=false; $('#render span').textContent='RENDER MASTER'; $('#outputStatus').textContent=job.status.toUpperCase();
    if(job.status==='completed'){ toast('Master rendered and logged'); await refreshJobs(); openDrawer(); } else toast(job.error || `Job ${job.status}`);
  } catch(error){toast(error.message);$('#render').disabled=false;}
}

async function refreshJobs(){const data=await api('/api/jobs');state.jobs=data.jobs;renderJobs();}
function renderJobs(){
  $('#jobCount').textContent=state.jobs.length; const root=$('#jobs'); if(!state.jobs.length){root.innerHTML='<p class="muted">No renders yet.</p>';return;}
  root.innerHTML=state.jobs.map(job=>`<article class="job"><div class="job-head"><b>${job.status.toUpperCase()}</b><span>${job.id}</span></div><p>${job.preset} · ${job.output.split('/').pop()}</p>${job.status==='completed'?`<a href="/media/renders/${encodeURIComponent(job.output.split('/').pop())}" download>DOWNLOAD MASTER →</a>`:''}</article>`).join('');
}
function openDrawer(){ $('#drawer').classList.add('open');$('#scrim').classList.add('open');$('#drawer').setAttribute('aria-hidden','false'); }
function closeDrawer(){ $('#drawer').classList.remove('open');$('#scrim').classList.remove('open');$('#drawer').setAttribute('aria-hidden','true'); }

$('#browse').onclick=()=>$('#fileInput').click(); $('#fileInput').onchange=e=>loadFile(e.target.files[0]);
['dragenter','dragover'].forEach(type=>$('#dropzone').addEventListener(type,e=>{e.preventDefault();$('#dropzone').classList.add('drag')}));
['dragleave','drop'].forEach(type=>$('#dropzone').addEventListener(type,e=>{e.preventDefault();$('#dropzone').classList.remove('drag')}));
$('#dropzone').addEventListener('drop',e=>loadFile(e.dataTransfer.files[0]));
$('#presetSearch').oninput=e=>renderPresets(e.target.value); $('#reset').onclick=()=>selectPreset(state.selected); $('#render').onclick=renderAudio;
$('#historyButton').onclick=openDrawer; $('#closeDrawer').onclick=closeDrawer; $('#scrim').onclick=closeDrawer;
$('#play').onclick=()=>{if(!audio.src)return toast('Load audio first');if(audio.paused){audio.play();$('#play span').textContent='Ⅱ'}else{audio.pause();$('#play span').textContent='▶'}};
$('#rewind').onclick=()=>audio.currentTime=0; audio.ontimeupdate=()=>{ $('#currentTime').textContent=formatTime(audio.currentTime);const fraction=audio.duration?audio.currentTime/audio.duration:0;$('#playhead').style.left=`calc(20px + ${fraction} * (100% - 40px))`;}; audio.onended=()=>$('#play span').textContent='▶';
$('#waveform').onclick=e=>{if(!audio.duration)return;const rect=e.target.getBoundingClientRect();audio.currentTime=(e.clientX-rect.left)/rect.width*audio.duration;};
window.onresize=()=>state.buffer&&drawWaveform(state.buffer);
boot();
