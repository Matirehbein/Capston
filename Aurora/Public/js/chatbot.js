const openChat   = document.getElementById('openChat');
const chatWindow = document.getElementById('chatWindow');
const closeChat  = document.getElementById('closeChat');
const sendBtn    = document.getElementById('sendBtn');
const chatBody   = document.getElementById('chatBody');
const userInput  = document.getElementById('userInput');

// Abrir con animación
openChat.addEventListener('click', () => {
  chatWindow.classList.add('show');         // pone display:flex
  // forzar reflow para que la transición ocurra
  void chatWindow.offsetWidth;
  chatWindow.classList.add('visible');      // anima transform/opacity
});

// Cerrar con animación
closeChat.addEventListener('click', () => {
  chatWindow.classList.remove('visible');   // inicia fade/slide out
  setTimeout(() => chatWindow.classList.remove('show'), 350); // quita del flujo
});

// Enviar mensaje
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', e => { if (e.key === 'Enter') sendMessage(); });

function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  const userMsg = document.createElement('div');
  userMsg.className = 'user-message';
  userMsg.innerHTML = `<p>${text}</p>`;
  chatBody.appendChild(userMsg);

  userInput.value = '';
  chatBody.scrollTop = chatBody.scrollHeight;

  setTimeout(() => {
    const botMsg = document.createElement('div');
    botMsg.className = 'bot-message';
    botMsg.innerHTML = `<p>Gracias por tu mensaje, estoy aprendiendo a responder 😉</p>`;
    chatBody.appendChild(botMsg);
    chatBody.scrollTop = chatBody.scrollHeight;
  }, 600);
}
