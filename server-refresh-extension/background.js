async function getServerTime(url) {
  const t0 = Date.now();
  try {
    const res = await fetch(url, { method: "HEAD", cache: "no-store" });
    const t1 = Date.now();
    const dateHeader = res.headers.get("Date");
    const serverBase = new Date(dateHeader).getTime();
    const latency = (t1 - t0) / 2;

    return {
      serverTime: serverBase + latency,
      localTime: t1
    };
  } catch (error) {
    console.error("서버 시간 획득 실패:", error);
    return { serverTime: Date.now(), localTime: Date.now() };
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "RESERVE_REFRESH") {
    (async () => {
      const { serverTime, localTime } = await getServerTime(msg.currentUrl);
      const offset = serverTime - localTime;

      const [h, m, s] = msg.targetTime.split(":").map(Number);
      const targetServer = new Date(serverTime);
      targetServer.setHours(h, m, s, 0);

      if (targetServer.getTime() <= serverTime) {
        targetServer.setDate(targetServer.getDate() + 1);
      }

      // 로컬 실행 시간 계산
      const alarmTime = targetServer.getTime() - offset;

      await chrome.storage.local.set({
        reservation: { tabId: msg.tabId }
      });

      await chrome.alarms.clear("REFRESH_ALARM");
      chrome.alarms.create("REFRESH_ALARM", { when: alarmTime });
      
      console.log(`[예약] 서버시간 ${msg.targetTime}에 새로고침 예정`);
    })();
  }
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "REFRESH_ALARM") {
    const { reservation } = await chrome.storage.local.get("reservation");
    if (reservation && reservation.tabId) {
      chrome.tabs.reload(reservation.tabId);
      await chrome.storage.local.remove("reservation");
    }
  }
});