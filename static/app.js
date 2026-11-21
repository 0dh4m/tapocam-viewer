/**
 * Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
 * Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
 * Author: Adham Cherkaoui Eddeqaqi (0dh4m) <0dh4mm@gmail.com>
 * GitHub: https://github.com/0dh4m
 */

(() => {
  // DOM Elements
  const pinOverlay = document.getElementById('pinOverlay');
  const pinCard = document.getElementById('pinCard');
  const pinError = document.getElementById('pinError');
  const pinDots = [
    document.getElementById('dot0'),
    document.getElementById('dot1'),
    document.getElementById('dot2'),
    document.getElementById('dot3')
  ];

  const cameraStream = document.getElementById('cameraStream');
  const videoStage = document.getElementById('videoStage');
  const liveStatusText = document.getElementById('liveStatusText');
  const liveDot = document.getElementById('liveDot');
  const liveClock = document.getElementById('liveClock');
  const camIpTag = document.getElementById('camIpTag');
  const offlineCard = document.getElementById('offlineCard');
  const cardSetupBtn = document.getElementById('cardSetupBtn');

  // Controls
  const streamHdBtn = document.getElementById('streamHdBtn');
  const streamSdBtn = document.getElementById('streamSdBtn');
  const audioToggleBtn = document.getElementById('audioToggleBtn');
  const audioIconMuted = document.getElementById('audioIconMuted');
  const audioIconUnmuted = document.getElementById('audioIconUnmuted');
  const snapshotBtn = document.getElementById('snapshotBtn');
  const fullscreenBtn = document.getElementById('fullscreenBtn');
  const lockBtn = document.getElementById('lockBtn');
  const testPingBtn = document.getElementById('testPingBtn');

  // Modals
  const settingsModal = document.getElementById('settingsModal');
  const openSettingsBtn = document.getElementById('openSettingsBtn');
  const closeSettingsModal = document.getElementById('closeSettingsModal');
  const settingsForm = document.getElementById('settingsForm');
  const modalTestBtn = document.getElementById('modalTestBtn');
  const settingsMsg = document.getElementById('settingsMsg');

  const deployModal = document.getElementById('deployModal');
  const deployGuideBtn = document.getElementById('deployGuideBtn');
  const closeDeployModal = document.getElementById('closeDeployModal');
  const gotItBtn = document.getElementById('gotItBtn');

  // State
  let enteredPin = '';
  let activeStream = 'tapo_hd';
  let isCheckingAuth = false;
  let statusPollTimer = null;

  // Realtime Clock
  function updateClock() {
    const now = new Date();
    liveClock.textContent = now.toTimeString().split(' ')[0] + ' LOC';
  }
  setInterval(updateClock, 1000);
  updateClock();

  // --- Auth Check on Load ---
  async function checkAuthStatus() {
    try {
      const res = await fetch('/api/auth/check');
      const data = await res.json();

      if (data.camera_ip) {
        camIpTag.textContent = `IP: ${data.camera_ip}`;
      }

      if (data.authenticated) {
        unlockDashboard(data);
      } else {
        lockDashboard();
      }
    } catch (e) {
      console.error("Auth check failed:", e);
      lockDashboard();
    }
  }

  function unlockDashboard(data) {
    pinOverlay.classList.add('hidden');
    enteredPin = '';
    updatePinDots();

    if (data && !data.camera_configured) {
      offlineCard.classList.remove('hidden');
      liveStatusText.textContent = 'CAMERA NOT CONFIGURED';
      liveDot.style.background = 'var(--accent-amber)';
    } else if (data && data.privacy_active) {
      offlineCard.classList.add('hidden');
      setConfidentialMode(true, false);
      startStatusPolling();
    } else {
      offlineCard.classList.add('hidden');
      setConfidentialMode(false, false);
      startVideoStream();
      startStatusPolling();
    }
  }

  function lockDashboard() {
    pinOverlay.classList.remove('hidden');
    stopVideoStream();
    stopStatusPolling();
    enteredPin = '';
    updatePinDots();
  }

  // --- PIN Keypad & Input Handling ---
  function updatePinDots() {
    pinDots.forEach((dot, idx) => {
      if (idx < enteredPin.length) {
        dot.classList.add('filled');
      } else {
        dot.classList.remove('filled');
      }
    });
  }

  async function handlePinDigit(digit) {
    if (enteredPin.length >= 4) return;
    enteredPin += digit;
    updatePinDots();

    if (enteredPin.length === 4) {
      await submitPin(enteredPin);
    }
  }

  function handlePinBackspace() {
    if (enteredPin.length > 0) {
      enteredPin = enteredPin.slice(0, -1);
      updatePinDots();
      pinError.textContent = '';
    }
  }

  function handlePinClear() {
    enteredPin = '';
    updatePinDots();
    pinError.textContent = '';
  }

  async function submitPin(pin) {
    if (isCheckingAuth) return;
    isCheckingAuth = true;
    pinError.textContent = 'Verifying security token...';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
      });

      const data = await res.json();
      if (data.success) {
        pinError.textContent = '';
        await checkAuthStatus();
      } else {
        triggerPinError(data.error || 'Incorrect PIN');
      }
    } catch (e) {
      triggerPinError('Network error connecting to security server');
    } finally {
      isCheckingAuth = false;
    }
  }

  function triggerPinError(msg) {
    pinError.textContent = msg;
    pinCard.classList.add('shake');
    setTimeout(() => {
      pinCard.classList.remove('shake');
      enteredPin = '';
      updatePinDots();
    }, 450);
  }

  // Keypad Click Events
  document.querySelectorAll('.key-btn[data-key]').forEach(btn => {
    btn.addEventListener('click', () => handlePinDigit(btn.getAttribute('data-key')));
  });
  document.getElementById('keypadBack').addEventListener('click', handlePinBackspace);
  document.getElementById('keypadClear').addEventListener('click', handlePinClear);

  // Keyboard support for PIN entry
  window.addEventListener('keydown', (e) => {
    if (!pinOverlay.classList.contains('hidden')) {
      if (e.key >= '0' && e.key <= '9') {
        handlePinDigit(e.key);
      } else if (e.key === 'Backspace') {
        handlePinBackspace();
      } else if (e.key === 'Escape') {
        handlePinClear();
      }
    }
  });

  // --- Video Stream Management ---
  async function startVideoStream() {
    if (isConfidentialActive) return;
    liveStatusText.textContent = 'CONNECTING STREAM...';
    liveDot.style.background = 'var(--accent-amber)';

    try {
      if (!customElements.get('video-stream')) {
        await customElements.whenDefined('video-stream');
      }
    } catch (e) {}

    if (cameraStream) {
      cameraStream.style.display = 'block';
      cameraStream.mode = 'webrtc,mse,mp4';
      cameraStream.src = new URL(`/ws?src=${activeStream}`, location.href);
    }
  }

  function stopVideoStream() {
    try {
      if (cameraStream) {
        cameraStream.ondisconnect?.();
        const vid = cameraStream.querySelector('video') || cameraStream.video;
        if (vid) {
          vid.pause();
          vid.srcObject = null;
          vid.removeAttribute('src');
          vid.load();
        }
        cameraStream.src = '';
        cameraStream.style.display = 'none';
      }
    } catch (e) {
      console.warn("Stop stream error:", e);
    }
  }

  // Stream Quality Toggle (HD / SD)
  streamHdBtn.addEventListener('click', () => {
    if (activeStream === 'tapo_hd') return;
    activeStream = 'tapo_hd';
    streamHdBtn.classList.add('selected');
    streamSdBtn.classList.remove('selected');
    startVideoStream();
  });

  streamSdBtn.addEventListener('click', () => {
    if (activeStream === 'tapo_sd') return;
    activeStream = 'tapo_sd';
    streamSdBtn.classList.add('selected');
    streamHdBtn.classList.remove('selected');
    startVideoStream();
  });

  // Audio Toggle
  audioToggleBtn.addEventListener('click', () => {
    const vid = cameraStream ? (cameraStream.querySelector('video') || cameraStream.video) : null;
    if (!vid) return;
    vid.muted = !vid.muted;
    if (vid.muted) {
      audioIconMuted.style.display = 'block';
      audioIconUnmuted.style.display = 'none';
      audioToggleBtn.classList.remove('active');
    } else {
      audioIconMuted.style.display = 'none';
      audioIconUnmuted.style.display = 'block';
      audioToggleBtn.classList.add('active');
    }
  });

  // Snapshot Capture
  snapshotBtn.addEventListener('click', () => {
    // Visual flash effect
    const flash = document.createElement('div');
    flash.style.position = 'absolute';
    flash.style.inset = '0';
    flash.style.background = 'rgba(255,255,255,0.7)';
    flash.style.zIndex = '50';
    flash.style.transition = 'opacity 0.4s ease';
    videoStage.appendChild(flash);
    setTimeout(() => {
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 400);
    }, 50);

    // Download snapshot
    const link = document.createElement('a');
    link.href = `/api/snapshot?src=${activeStream}&t=${Date.now()}`;
    link.download = `tapo_snapshot_${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  });

  // Fullscreen
  fullscreenBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      videoStage.requestFullscreen().catch(err => alert(`Fullscreen error: ${err.message}`));
    } else {
      document.exitFullscreen();
    }
  });

  // Lock Button
  lockBtn.addEventListener('click', async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    lockDashboard();
  });

  // --- Status Polling ---
  function startStatusPolling() {
    stopStatusPolling();
    pollStatus();
    statusPollTimer = setInterval(pollStatus, 4000);
  }

  function stopStatusPolling() {
    if (statusPollTimer) {
      clearInterval(statusPollTimer);
      statusPollTimer = null;
    }
  }

  async function pollStatus() {
    if (isConfidentialActive) return;
    try {
      const res = await fetch('/api/stream/status');
      const data = await res.json();
      
      const isOnline = activeStream === 'tapo_hd' ? data.hd_online : data.sd_online;
      if (isOnline || data.engine_online) {
        liveStatusText.textContent = `LIVE • ${activeStream === 'tapo_hd' ? '2K HD' : 'SD'}`;
        liveDot.style.background = 'var(--accent-rose)';
      } else {
        liveStatusText.textContent = 'CONNECTING...';
        liveDot.style.background = 'var(--accent-amber)';
      }
    } catch (e) {
      liveStatusText.textContent = 'RECONNECTING...';
      liveDot.style.background = 'var(--accent-rose)';
    }
  }

  // --- Settings Modal Handling ---
  async function openSettings() {
    settingsModal.classList.remove('hidden');
    settingsMsg.textContent = '';
    
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        document.getElementById('cfgIp').value = data.ip || '';
        document.getElementById('cfgUsername').value = data.username || '';
        document.getElementById('cfgPassword').placeholder = data.has_password ? '•••••••• (Saved)' : 'Enter camera password';
      }
    } catch (e) {}
  }

  openSettingsBtn.addEventListener('click', openSettings);
  cardSetupBtn.addEventListener('click', openSettings);

  closeSettingsModal.addEventListener('click', () => {
    settingsModal.classList.add('hidden');
  });

  // Test Camera Ping
  async function testCameraConnection() {
    testPingBtn.innerHTML = 'Pinging Camera...';
    modalTestBtn.innerHTML = 'Testing...';

    try {
      const res = await fetch('/api/camera/test');
      const data = await res.json();

      if (data.reachable) {
        alert(`✅ Success: ${data.message}`);
      } else {
        alert(`❌ Camera Unreachable: ${data.error}`);
      }
    } catch (e) {
      alert(`❌ Network error pinging camera: ${e.message}`);
    } finally {
      testPingBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg><span>Test Camera Ping</span>`;
      modalTestBtn.innerHTML = 'Test Connection';
    }
  }

  testPingBtn.addEventListener('click', testCameraConnection);
  modalTestBtn.addEventListener('click', testCameraConnection);

  // Save Settings Form
  settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    settingsMsg.style.color = 'var(--accent-cyan)';
    settingsMsg.textContent = 'Saving configuration & restarting streaming engine...';

    const ip = document.getElementById('cfgIp').value.trim();
    const username = document.getElementById('cfgUsername').value.trim();
    const password = document.getElementById('cfgPassword').value.trim();
    const newPin = document.getElementById('cfgPin').value.trim();

    try {
      const cfgPayload = { ip, username };
      if (password) cfgPayload.password = password;

      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfgPayload)
      });
      const data = await res.json();

      // If PIN is also being updated
      if (newPin && newPin.length >= 4) {
        await fetch('/api/auth/set_pin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pin: newPin })
        });
      }

      if (data.success) {
        settingsMsg.style.color = 'var(--accent-emerald)';
        settingsMsg.textContent = '✅ Saved! Connecting to live camera...';
        setTimeout(() => {
          settingsModal.classList.add('hidden');
          checkAuthStatus();
        }, 1200);
      } else {
        settingsMsg.style.color = 'var(--accent-rose)';
        settingsMsg.textContent = `❌ ${data.error || 'Failed to save configuration'}`;
      }
    } catch (err) {
      settingsMsg.style.color = 'var(--accent-rose)';
      settingsMsg.textContent = `❌ Error: ${err.message}`;
    }
  });

  // Deploy Guide Modal
  deployGuideBtn.addEventListener('click', () => deployModal.classList.remove('hidden'));
  closeDeployModal.addEventListener('click', () => deployModal.classList.add('hidden'));
  gotItBtn.addEventListener('click', () => deployModal.classList.add('hidden'));

  // Close modals on backdrop click
  window.addEventListener('click', (e) => {
    if (e.target === settingsModal) settingsModal.classList.add('hidden');
    if (e.target === deployModal) deployModal.classList.add('hidden');
  });

  // --- PTZ Camera Direction Controller ---
  let ptzStep = 0.12;
  const ptzStatus = document.getElementById('ptzStatus');
  let isPtzMoving = false;

  async function sendPtzMove(direction) {
    if (isPtzMoving) return;
    if (isConfidentialActive) {
      if (ptzStatus) {
        ptzStatus.textContent = 'LOCKED (PRIVACY)';
        ptzStatus.style.color = '#c084fc';
      }
      return;
    }
    isPtzMoving = true;
    
    if (ptzStatus) {
      ptzStatus.textContent = 'MOVING...';
      ptzStatus.style.color = 'var(--accent-amber)';
    }

    try {
      const res = await fetch('/api/ptz/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction, step: ptzStep })
      });
      const data = await res.json();
      if (!data.success) {
        console.warn('PTZ error:', data.message);
      }
    } catch (e) {
      console.error('PTZ request failed:', e);
    } finally {
      setTimeout(() => {
        isPtzMoving = false;
        if (ptzStatus) {
          ptzStatus.textContent = isConfidentialActive ? 'LOCKED' : 'READY';
          ptzStatus.style.color = isConfidentialActive ? '#c084fc' : 'var(--accent-cyan)';
        }
      }, 250);
    }
  }

  // D-Pad Click Listeners
  document.querySelectorAll('.dpad-btn[data-dir]').forEach(btn => {
    btn.addEventListener('click', () => {
      const dir = btn.getAttribute('data-dir');
      sendPtzMove(dir);
    });
  });

  // Step Angle Buttons (Fine, Medium, Wide)
  document.querySelectorAll('.ptz-step-opt').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.ptz-step-opt').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      ptzStep = parseFloat(btn.getAttribute('data-step')) || 0.12;
    });
  });

  // Keyboard Arrow Keys (When unlocked & not typing in input)
  window.addEventListener('keydown', (e) => {
    if (pinOverlay && !pinOverlay.classList.contains('hidden')) return;
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      sendPtzMove('up');
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      sendPtzMove('down');
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      sendPtzMove('left');
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      sendPtzMove('right');
    } else if (e.key === 'c' || e.key === 'C') {
      e.preventDefault();
      setConfidentialMode(!isConfidentialActive);
    }
  });

  // --- Confidential / Privacy Mode ---
  let isConfidentialActive = false;
  const confidentialBtn = document.getElementById('confidentialBtn');
  const confidentialBtnText = document.getElementById('confidentialBtnText');
  const confidentialCard = document.getElementById('confidentialCard');
  const disableConfidentialBtn = document.getElementById('disableConfidentialBtn');

  async function setConfidentialMode(active, syncServer = true) {
    isConfidentialActive = active;

    if (active) {
      confidentialBtn?.classList.add('active');
      if (confidentialBtnText) confidentialBtnText.textContent = '🔒 وضع السرية مفعل';
      confidentialCard?.classList.remove('hidden');
      stopVideoStream();
      liveStatusText.textContent = '🔒 CONFIDENTIAL • LENS TUCKED & STREAM OFF';
      liveDot.style.background = '#a855f7';
      if (ptzStatus) {
        ptzStatus.textContent = 'LOCKED';
        ptzStatus.style.color = '#c084fc';
      }
    } else {
      confidentialBtn?.classList.remove('active');
      if (confidentialBtnText) confidentialBtnText.textContent = 'Confidential Mode';
      confidentialCard?.classList.add('hidden');
      if (ptzStatus) {
        ptzStatus.textContent = 'READY';
        ptzStatus.style.color = 'var(--accent-cyan)';
      }
      startVideoStream();
      liveStatusText.textContent = 'CONNECTING...';
      liveDot.style.background = 'var(--accent-amber)';
    }

    if (syncServer) {
      try {
        await fetch('/api/privacy/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enable: active })
        });
      } catch (e) {
        console.error('Privacy toggle error:', e);
      }
    }
  }

  confidentialBtn?.addEventListener('click', () => setConfidentialMode(!isConfidentialActive));
  disableConfidentialBtn?.addEventListener('click', () => setConfidentialMode(false));

  // Start initialization
  checkAuthStatus();
})();
