let timeOffset = null;

async function syncPreciseTime() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  // SSAFY 사이트가 아닐 경우 기본적으로 SSAFY 서버에 요청
  const targetUrl = tab?.url?.includes("ssafy.com") ? tab.url : "https://edu.ssafy.com/edu/main/index.do";

  try {
    const startRes = await fetch(targetUrl, { method: "HEAD", cache: "no-store" });
    let lastDate = startRes.headers.get("Date");
    
    // 초 단위가 바뀌는 지점을 포착하여 밀리초 오차 보정
    for (let i = 0; i < 20; i++) {
      const check = await fetch(targetUrl, { method: "HEAD", cache: "no-store" });
      const currentDate = check.headers.get("Date");
      
      if (currentDate !== lastDate) {
        const syncPoint = Date.now();
        const serverTime = new Date(currentDate).getTime();
        timeOffset = serverTime - syncPoint;
        break;
      }
      await new Promise(r => setTimeout(r, 100));
    }
  } catch (e) {
    console.error("서버 시각 로드 실패:", e);
    document.getElementById("status").textContent = "서버 시각을 불러올 수 없습니다.";
  }
}

function getServerNow() {
  return timeOffset === null ? null : Date.now() + timeOffset;
}

document.addEventListener("DOMContentLoaded", async () => {
  const serverTimeEl = document.getElementById("serverTime");
  const reserveBtn = document.getElementById("reserveBtn");
  const statusEl = document.getElementById("status");

  setInterval(() => {
    const now = getServerNow();
    if (!now) return;
    serverTimeEl.textContent = new Date(now).toLocaleTimeString("ko-KR", {
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
    });
  }, 50);

  await syncPreciseTime();

  reserveBtn.addEventListener("click", async () => {
    const h = document.getElementById("hour").value;
    const m = document.getElementById("minute").value;
    const s = document.getElementById("second").value || "0";

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.runtime.sendMessage({
      type: "RESERVE_CHECKOUT",
      targetTime: `${h}:${m}:${s}`,
      tabId: tab.id,
      currentUrl: tab.url.includes("ssafy.com") ? tab.url : "https://edu.ssafy.com/edu/main/index.do"
    });

    statusEl.textContent = `예약 완료: ${h}시 ${m}분 ${s}초`;
    statusEl.classList.add("status-active");
  });
});