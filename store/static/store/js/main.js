// ===========================================
// 🛒 CART SYSTEM WITH FETCH API
// ===========================================
class PerfumeCart {
  constructor(apiUrl = '/api') {
    this.apiUrl = apiUrl;
    this.cart = [];
    this.isLoading = false;
    this.init();
  }

  init() {
    // جلب السلة عند تحميل الصفحة
    this.fetchCart();
  }

  setLoading(loading) {
    this.isLoading = loading;
  }

  // جلب السلة من السيرفر
  async fetchCart() {
    try {
      this.setLoading(true);
      const response = await fetch(`${this.apiUrl}/cart`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      this.cart = data.items || [];
      this.updateCartUI();
      return data;
    } catch (error) {
      console.error('❌ خطأ في جلب السلة:', error);
      // في حالة فشل الـ API، نستخدم array فارغ
      this.cart = [];
    } finally {
      this.setLoading(false);
    }
  }

  // إضافة عطر للسلة
  async addToCart(perfumeId, quantity = 1, productName = 'المنتج') {
    try {
      this.setLoading(true);
      const response = await fetch(`${this.apiUrl}/cart/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ perfume_id: perfumeId, quantity })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      this.cart = data.items || [];
      this.updateCartUI();
      console.log(`✅ تم إضافة ${productName} إلى السلة`);
      return data;
    } catch (error) {
      console.error('❌ خطأ في إضافة المنتج:', error);
      // في حالة فشل الـ API، نضيف محلياً (fallback)
      this.cart.push({ id: Date.now(), name: productName, quantity });
      this.updateCartUI();
    } finally {
      this.setLoading(false);
    }
  }

  // تحديث الكمية
  async updateQuantity(itemId, quantity) {
    if (quantity < 1) return this.removeFromCart(itemId);

    try {
      this.setLoading(true);
      const response = await fetch(`${this.apiUrl}/cart/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ item_id: itemId, quantity })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      this.cart = data.items || [];
      this.updateCartUI();
      return data;
    } catch (error) {
      console.error('❌ خطأ في التحديث:', error);
    } finally {
      this.setLoading(false);
    }
  }

  // حذف من السلة
  async removeFromCart(itemId) {
    try {
      this.setLoading(true);
      const response = await fetch(`${this.apiUrl}/cart/remove/${itemId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      this.cart = data.items || [];
      this.updateCartUI();
      return data;
    } catch (error) {
      console.error('❌ خطأ في الحذف:', error);
    } finally {
      this.setLoading(false);
    }
  }

  // تفريغ السلة
  async clearCart() {
    try {
      this.setLoading(true);
      const response = await fetch(`${this.apiUrl}/cart/clear`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      this.cart = [];
      this.updateCartUI();
    } catch (error) {
      console.error('❌ خطأ في التفريغ:', error);
    } finally {
      this.setLoading(false);
    }
  }

  // عدد المنتجات
  getItemCount() {
    return this.cart.reduce((count, item) => count + (item.quantity || 1), 0);
  }

  // تحديث الواجهة
  updateCartUI() {
    const cartCount = document.querySelector('.cart-count');
    if (cartCount) {
      const count = this.getItemCount();
      cartCount.textContent = count;
      cartCount.style.display = count > 0 ? 'inline-block' : 'none';
    }
  }
}

// إنشاء كائن السلة
const cart = new PerfumeCart('/api');

// ===========================================
// 🎨 FEATURE FLAGS SYSTEM
// ===========================================
class FeatureFlags {
  constructor() {
    this.flags = { 
      darkTheme: false,
      promoBanner: false,
      categories: false
    };
    this.init();
  }

  init() {
    document.querySelectorAll('.toggle').forEach(toggle => {
      toggle.addEventListener('click', () => {
        const flagName = toggle.dataset.flag; 
        this.toggleFlag(flagName);
        toggle.classList.toggle('active');
      });
    });
    this.applyFlags();
  }

  toggleFlag(flagName) {
    this.flags[flagName] = !this.flags[flagName];
    this.applyFlags();
    console.log(`Feature Flag "${flagName}" is now: ${this.flags[flagName]}`);
  }

  isEnabled(flagName) {
    return this.flags[flagName];
  }

  applyFlags() {
    if (this.isEnabled('darkTheme')) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }

    const promoBanner = document.getElementById('promoBanner');
    if (promoBanner) {
      promoBanner.style.display = this.isEnabled('promoBanner') ? 'block' : 'none';
    }

    const categories = document.getElementById('categories');
    if (categories) {
      categories.style.display = this.isEnabled('categories') ? 'grid' : 'none';
    }
  }
}

const featureFlags = new FeatureFlags();

// ===========================================
// 🛍️ PRODUCT BUTTONS (مع ربط السلة)
// ===========================================
document.querySelectorAll('.product-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    const productName = this.parentElement.querySelector('.product-name').textContent;
    const productId = this.dataset.productId || Date.now(); // لو ما في ID نستخدم timestamp
    
    // إضافة للسلة عن طريق الـ API
    cart.addToCart(productId, 1, productName);
    
    // تغيير شكل الزر
    this.textContent = 'تم الإضافة!';
    this.style.background = '#27ae60';
    
    setTimeout(() => {
      this.textContent = this.getAttribute('data-ar') || 'اشتري الآن';
      this.style.background = '#a9745b';
    }, 2000);
  });
});

// ===========================================
// 🔗 SMOOTH SCROLLING
// ===========================================
document.querySelectorAll('nav a').forEach(link => {
  link.addEventListener('click', function(e) {
    e.preventDefault();
    const targetId = this.getAttribute('href');
    if (targetId.startsWith('#')) {
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth' });
      }
    }
  });
});

// ===========================================
// 🌐 LANGUAGE SWITCHER (نسخة محسّنة بدون تكرار)
// ===========================================
let currentLang = 'ar';

const langSwitch = document.getElementById('langSwitch') || document.getElementById('toggleLang');

if (langSwitch) {
  langSwitch.addEventListener('click', () => {
    currentLang = currentLang === 'ar' ? 'en' : 'ar';
    langSwitch.textContent = currentLang === 'ar' ? 'EN' : 'AR';

    document.querySelectorAll('[data-ar]').forEach(el => {
      const newText = currentLang === 'ar' ? el.dataset.ar : el.dataset.en;
      if (el.tagName.toLowerCase() === 'input' || el.tagName.toLowerCase() === 'button') {
        el.value = newText;
        el.textContent = newText;
      } else {
        el.innerHTML = newText;
      }
    });

    // RTL/LTR
    document.documentElement.dir = currentLang === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = currentLang;
  });
}

// ===========================================
// 🔐 LOGIN FORM (من 1.js)
// ===========================================
document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  const message = document.getElementById('message');

  if (loginForm && message) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value.trim();

      if (email === "user@example.com" && password === "123456") {
        message.textContent = "Login Successful! Welcome to My Fragrance.";
        message.style.color = "green";
      } else {
        message.textContent = "Invalid email or password. Please try again.";
        message.style.color = "red";
      }

      loginForm.reset();
    });
  }

  // تهيئة كارد الطقس والوقت
  initWeatherCard();
});

// ===========================================
// WEATHER & TIME CARD
// ===========================================
class WeatherTimeCard {
  constructor() {
    this.cardElement = null;
    this.updateInterval = null;
  }

  // إنشاء الكارد في الصفحة
  createCard() {
    const card = document.createElement('div');
    card.id = 'weatherTimeCard';
    card.innerHTML = `
      <div class="weather-card">
        <div class="weather-header">
          <span class="weather-icon">🌤️</span>
          <h3>الطقس والوقت</h3>
        </div>
        <div class="weather-body">
          <div class="time-section">
            <div class="current-time" id="currentTime">--:--:--</div>
            <div class="current-date" id="currentDate">---</div>
          </div>
          <div class="weather-section" id="weatherSection">
            <div class="loading-weather">⏳ جاري تحميل بيانات الطقس...</div>
          </div>
        </div>
        <button class="refresh-weather-btn" onclick="weatherCard.refreshWeather()">
          🔄 تحديث
        </button>
      </div>
    `;
    this.cardElement = card;
    return card;
  }

  // تحديث الوقت والتاريخ
  updateTime() {
    const now = new Date();
    const timeElement = document.getElementById('currentTime');
    const dateElement = document.getElementById('currentDate');

    if (timeElement && dateElement) {
      const timeStr = now.toLocaleTimeString('ar-SA', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });

      const dateStr = now.toLocaleDateString('ar-SA', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });

      timeElement.textContent = timeStr;
      dateElement.textContent = dateStr;
    }
  }

  // جلب بيانات الطقس من API
  async fetchWeather() {
    try {
      // إحداثيات جدة (يمكنك تغييرها لمدينتك)
      const lat = 21.4858;
      const lon = 39.1925;
      
      const response = await fetch(
        `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true&timezone=auto`
      );

      if (!response.ok) throw new Error('فشل في جلب بيانات الطقس');

      const data = await response.json();
      return data.current_weather;
    } catch (error) {
      console.error('خطأ في جلب الطقس:', error);
      throw error;
    }
  }

  // تحديث واجهة الطقس
  async updateWeather() {
    const weatherSection = document.getElementById('weatherSection');
    
    if (!weatherSection) return;

    weatherSection.innerHTML = '<div class="loading-weather">⏳ جاري التحميل...</div>';

    try {
      const weather = await this.fetchWeather();
      const temp = Math.round(weather.temperature);
      const windSpeed = Math.round(weather.windspeed);

      // تحديد وصف الطقس بناءً على درجة الحرارة
      let weatherDesc = '☀️ مشمس';
      if (temp > 35) weatherDesc = '🔥 حار جداً';
      else if (temp > 25) weatherDesc = '☀️ دافئ';
      else if (temp > 15) weatherDesc = '🌤️ معتدل';
      else weatherDesc = '❄️ بارد';

      weatherSection.innerHTML = `
        <div class="weather-info">
          <div class="weather-temp">${temp}°C</div>
          <div class="weather-desc">${weatherDesc}</div>
          <div class="weather-details">
            <div class="weather-detail">
              <span class="detail-label">💨 الرياح</span>
              <span class="detail-value">${windSpeed} كم/س</span>
            </div>
            <div class="weather-detail">
              <span class="detail-label">📍 الموقع</span>
              <span class="detail-value">جدة</span>
            </div>
          </div>
        </div>
      `;
    } catch (error) {
      weatherSection.innerHTML = `
        <div class="weather-error">
          ❌ فشل في تحميل بيانات الطقس
          <br><small>تحقق من الاتصال بالإنترنت</small>
        </div>
      `;
    }
  }

  // تحديث الطقس يدوياً
  async refreshWeather() {
    await this.updateWeather();
  }

  // تشغيل الكارد
  start() {
    // تحديث الوقت فوراً
    this.updateTime();
    // تحديث الطقس فوراً
    this.updateWeather();

    // تحديث الوقت كل ثانية
    this.updateInterval = setInterval(() => {
      this.updateTime();
    }, 1000);

    // تحديث الطقس كل 10 دقائق
    setInterval(() => {
      this.updateWeather();
    }, 600000);
  }

  // إيقاف التحديثات
  stop() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
  }
}

// إنشاء الكارد وتشغيله
let weatherCard;

function initWeatherCard() {
  // إنشاء كائن الكارد
  weatherCard = new WeatherTimeCard();
  
  // البحث عن مكان لإضافة الكارد
  const container = document.getElementById('weatherContainer') || document.body;
container.appendChild(weatherCard.createCard());

  
  // إضافة الكارد للصفحة
  const cardElement = weatherCard.createCard();
  container.insertBefore(cardElement, container.firstChild);
  
  // إضافة الـ CSS للكارد
  addWeatherCardStyles();
  
  // تشغيل الكارد
  weatherCard.start();
}

// إضافة الأنماط (CSS) للكارد
function addWeatherCardStyles() {
  if (document.getElementById('weatherCardStyles')) return;
  
  const style = document.createElement('style');
  style.id = 'weatherCardStyles';
  style.textContent = `
    .weather-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 20px;
      padding: 25px;
      margin: 20px auto;
      max-width: 500px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.2);
      color: white;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .weather-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 20px;
      padding-bottom: 15px;
      border-bottom: 2px solid rgba(255,255,255,0.2);
    }

    .weather-icon {
      font-size: 2rem;
    }

    .weather-header h3 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: bold;
    }

    .weather-body {
      margin-bottom: 20px;
    }

    .time-section {
      text-align: center;
      margin-bottom: 25px;
    }

    .current-time {
      font-size: 3rem;
      font-weight: bold;
      margin-bottom: 10px;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }

    .current-date {
      font-size: 1.1rem;
      opacity: 0.9;
    }

    .weather-section {
      background: rgba(255,255,255,0.15);
      border-radius: 15px;
      padding: 20px;
      backdrop-filter: blur(10px);
    }

    .loading-weather {
      text-align: center;
      padding: 20px;
      font-size: 1rem;
    }

    .weather-info {
      text-align: center;
    }

    .weather-temp {
      font-size: 3.5rem;
      font-weight: bold;
      margin-bottom: 10px;
    }

    .weather-desc {
      font-size: 1.3rem;
      margin-bottom: 20px;
      opacity: 0.95;
    }

    .weather-details {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      margin-top: 20px;
    }

    .weather-detail {
      background: rgba(255,255,255,0.1);
      padding: 12px;
      border-radius: 10px;
      text-align: center;
    }

    .detail-label {
      display: block;
      font-size: 0.9rem;
      opacity: 0.8;
      margin-bottom: 5px;
    }

    .detail-value {
      display: block;
      font-size: 1.1rem;
      font-weight: bold;
    }

    .weather-error {
      text-align: center;
      padding: 20px;
      font-size: 0.95rem;
      opacity: 0.9;
    }

    .weather-error small {
      opacity: 0.7;
    }

    .refresh-weather-btn {
      width: 100%;
      background: rgba(255,255,255,0.2);
      border: 2px solid rgba(255,255,255,0.3);
      color: white;
      padding: 12px;
      border-radius: 10px;
      font-size: 1rem;
      cursor: pointer;
      transition: all 0.3s ease;
      font-weight: bold;
    }

    .refresh-weather-btn:hover {
      background: rgba(255,255,255,0.3);
      border-color: rgba(255,255,255,0.5);
      transform: translateY(-2px);
    }

    .refresh-weather-btn:active {
      transform: translateY(0);
    }

    @media (max-width: 600px) {
      .weather-card {
        margin: 10px;
        padding: 20px;
      }

      .current-time {
        font-size: 2.5rem;
      }

      .weather-temp {
        font-size: 3rem;
      }
    }
  `;
  
  document.head.appendChild(style);
}