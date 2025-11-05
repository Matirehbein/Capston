//-------------------------------------------------------
// 1. Referencias a elementos del DOM
//-------------------------------------------------------
const openChat   = document.getElementById('openChat');
const chatWindow = document.getElementById('chatWindow');
const closeChat  = document.getElementById('closeChat');
const sendBtn    = document.getElementById('sendBtn');
const chatBody   = document.getElementById('chatBody');
const userInput  = document.getElementById('userInput');

// Variable para almacenar el sessionId de Flask o uno temporal
let sessionUserId = null;

//-------------------------------------------------------
// 2. Obtener session_id de Flask al cargar la página
//-------------------------------------------------------
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('http://localhost:5000/api/session_info', { credentials: 'include' });
    const data = await res.json();

    if (data.logged_in) {
      sessionUserId = data.id; // user_id desde Flask
      console.log("✅ Sesión Flask detectada. ID:", sessionUserId);
    } else {
      sessionUserId = "guest-" + crypto.randomUUID();
      console.log("ℹ Usuario no logueado. ID temporal:", sessionUserId);
    }
  } catch (error) {
    console.error("❌ Error obteniendo session_info:", error);
    sessionUserId = "guest-" + crypto.randomUUID();
  }
});

//-------------------------------------------------------
// 3. Abrir y cerrar chat con animaciones
//-------------------------------------------------------
openChat.addEventListener('click', () => {
  chatWindow.classList.add('show');
  void chatWindow.offsetWidth; // Forzar reflow
  chatWindow.classList.add('visible');
});

closeChat.addEventListener('click', () => {
  chatWindow.classList.remove('visible');
  setTimeout(() => chatWindow.classList.remove('show'), 350);
});

//-------------------------------------------------------
// 4. Eventos de envío de mensaje
//-------------------------------------------------------
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', e => {
  if (e.key === 'Enter') sendMessage();
});

//-------------------------------------------------------
// 5. Función principal: enviar mensaje a n8n + mostrar respuesta
//-------------------------------------------------------
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  // 5.1 Mostrar mensaje del usuario
  const userMsg = document.createElement('div');
  userMsg.className = 'user-message';
  userMsg.innerHTML = `<p>${text}</p>`;
  chatBody.appendChild(userMsg);
  chatBody.scrollTop = chatBody.scrollHeight;
  userInput.value = '';

  // 5.2 Llamar a API del chatbot (n8n)
  try {
    const res = await fetch(
      "https://vicmoralesl.app.n8n.cloud/webhook/fd272f2c-66c0-4d7c-a04e-f239f0c90509/chat", 
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "sendMessage",
          sessionId: sessionUserId || "unknown-user",
          chatInput: text
        })
      }
    );

    const data = await res.json();
    const reply = data.reply || "⚠️ No recibí respuesta del chatbot.";

    // 5.3 Mostrar mensaje del bot
    const botMsg = document.createElement('div');
    botMsg.className = 'bot-message';
    botMsg.innerHTML = `<p>${reply}</p>`;
    chatBody.appendChild(botMsg);
    chatBody.scrollTop = chatBody.scrollHeight;

  } catch (error) {
    console.error("❌ Error enviando a la API del chatbot:", error);
    const botMsg = document.createElement('div');
    botMsg.className = 'bot-message';
    botMsg.innerHTML = `<p>❌ Error al conectar con el chatbot. Intenta más tarde.</p>`;
    chatBody.appendChild(botMsg);
  }
}
