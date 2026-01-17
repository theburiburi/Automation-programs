let timeOffset = null;

/**
 * 정밀 서버 시간 동기화
 * 서버 헤더의 초(Second)가 바뀌는 시점을 포착하여 밀리초 오차를 최소화합니다.
 */
async function syncDisplayTime() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return;

  try {
    // 1. 초기 샘플링
    const start = Date.now();
    const res = await fetch(tab.url, { method: "HEAD", cache: "no-store" });
    const initialDate = res.headers.get("Date");
    
    // 2. 서버의 '초'가 바뀔 때까지 루프를 돌며 정밀 측정 (최대 1.5초)
    let lastDate = initialDate;
    let syncPoint = Date.now();
    
    // 서버 헤더 값이 변하는 순간을 포착
    for (let i = 0; i < 10; i++) {
      const checkRes = await fetch(tab.url, { method: "HEAD", cache: "no-store" });
      const currentDate = checkRes.headers.get("Date");
      
      if (currentDate !== lastDate) {
        // 초가 바뀌는 시점을 잡음
        syncPoint = Date.now();
        const serverTime = new Date(currentDate).getTime();
        // 헤더는 초의 시작(000ms)을 의미하므로 현재 로컬 시간과의 차이 계산
        timeOffset = serverTime - syncPoint;
        break;
      }
      // 잠시 대기 후 재시도
      await new Promise(r => setTimeout(r, 100));
    }

    // 루프에서 못 잡았을 경우 일반적인 방식으로 보정
    if (timeOffset === null) {
      const end = Date.now();
      const serverTime = new Date(initialDate).getTime();
      const latency = (end - start) / 2;
      // 초 단위 버림 보정을 위해 500ms 추가 보정 (경험적 수치)
      timeOffset = (serverTime + 500) + latency - end;
    }
  } catch (e) {
    console.error("정밀 동기화 실패:", e);
  }
}

function getServerNow() {
  return timeOffset === null ? null : Date.now() + timeOffset;
}

document.addEventListener("DOMContentLoaded", async () => {
  const serverTimeEl = document.getElementById("serverTime");
  const reserveBtn = document.getElementById("reserveBtn");
  const statusEl = document.getElementById("status");

  // 시계 업데이트 (밀리초 단위 반영을 위해 50ms 주기로 실행)
  setInterval(() => {
    const now = getServerNow();
    if (!now) return;
    
    const date = new Date(now);
    serverTimeEl.textContent = date.toLocaleTimeString("ko-KR", {
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
    });
    
    // (선택사항) 밀리초 확인용
    // serverTimeEl.textContent += "." + String(date.getMilliseconds()).padStart(3, '0');
  }, 50);

  serverTimeEl.textContent = "정밀 동기화 중...";
  await syncDisplayTime();

  reserveBtn.addEventListener("click", async () => {
    const h = document.getElementById("hour").value;
    const m = document.getElementById("minute").value;
    const s = document.getElementById("second").value || "0";

    if (h === "" || m === "") {
      statusEl.textContent = "시간을 입력해주세요.";
      return;
    }

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.runtime.sendMessage({
      type: "RESERVE_REFRESH",
      targetTime: `${h}:${m}:${s}`,
      tabId: tab.id,
      currentUrl: tab.url
    });

    statusEl.textContent = `예약 완료! (${h}:${m}:${s})`;
  });
});