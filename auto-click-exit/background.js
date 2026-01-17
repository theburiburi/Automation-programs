async function getServerTime(url) {
  const t0 = Date.now();
  try {
    const res = await fetch(url, { method: "HEAD", cache: "no-store" });
    const t1 = Date.now();
    const dateHeader = res.headers.get("Date");
    const serverBase = new Date(dateHeader).getTime();
    
    // RTT(왕복 시간)의 절반을 더해 네트워크 지연 보정
    return { serverTime: serverBase + (t1 - t0) / 2, localTime: t1 };
  } catch (e) {
    return { serverTime: Date.now(), localTime: Date.now() };
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "RESERVE_CHECKOUT") {
    (async () => {
      const { serverTime, localTime } = await getServerTime(msg.currentUrl);
      const offset = serverTime - localTime;

      const [h, m, s] = msg.targetTime.split(":").map(Number);
      const targetServer = new Date(serverTime);
      targetServer.setHours(h, m, s, 0);

      if (targetServer.getTime() <= serverTime) {
        targetServer.setDate(targetServer.getDate() + 1);
      }

      // 로컬 컴퓨터가 알람을 울려야 할 시간 계산
      const alarmTime = targetServer.getTime() - offset;

      await chrome.storage.local.set({ reservation: { tabId: msg.tabId } });
      await chrome.alarms.clear("CHECKOUT_ALARM");
      chrome.alarms.create("CHECKOUT_ALARM", { when: alarmTime });
    })();
  }
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "CHECKOUT_ALARM") {
    const { reservation } = await chrome.storage.local.get("reservation");
    if (!reservation) return;

    chrome.tabs.reload(reservation.tabId, {}, () => {
      setTimeout(() => {
        chrome.scripting.executeScript({
          target: { tabId: reservation.tabId },
          func: clickCheckoutLogic
        });
      }, 3000); // 페이지 로딩 대기
    });
  }
});

function clickCheckoutLogic() {
  const targets = ["퇴실", "퇴실하기"];
  const buttons = Array.from(document.querySelectorAll('button, a, input[type="button"]'));
  const btn = buttons.find(b => 
    targets.some(t => b.textContent.includes(t) || (b.value && b.value.includes(t)))
  );

  if (btn) {
    btn.click();
    // 확인 모달창이 뜨는 경우 승인 로직 (필요시 추가)
    setTimeout(() => {
      const confirmBtn = document.querySelector('.btn_confirm, .ok, .ui-button');
      if (confirmBtn) confirmBtn.click();
    }, 1000);
  }
}