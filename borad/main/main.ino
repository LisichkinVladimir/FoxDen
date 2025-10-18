#include <inttypes.h>
#include <main.h>
#include <web.h>
#include <Bounce2.h>
#include <pulse_led.h>

// Пины к которым подключены устройства
static uint8_t GPIOPin[PIN_COUNT] = {0, 1};
// Bounce объект для счетчика, помогающий избежать закрытии или открытии множества нежелательных ложных состояний (похожих на шум)
Bounce bounce[PIN_COUNT] = {};

void setup() {
  #ifdef DEBUG_MODE  
  Serial.begin(115200);
  delay(1000);
  Serial.println("Setup-----------------------------------");
  #endif
  // Инициализируем светодиод
  initLed();
  // Инициализируем структуры для работы с Web/WiFi
  initWeb();
  // Инициализируем пины
  for(int i = 0; i < PIN_COUNT; i++) {
    // Каждый вывод имеет нагрузочный резистор (по умолчанию отключен) 20-50 кОм и может пропускать до 40 мА. - включается командой INPUT_PULLUP  
    //pinMode(GPIOPin, INPUT_PULLUP); // Инициализируем пин и включаем подтягивающий резистор
    bounce[i].attach(GPIOPin[i], INPUT_PULLUP);
    // Время максимального "маргания"
    bounce[i].interval(10);
  }
}

void loop() {
  delay(1000);
  for(int i = 0; i < PIN_COUNT; i++) {
    int val = digitalRead(GPIOPin[i]);
    #ifdef DEBUG_MODE  
    static int step = 0;
    Serial.printf("GPIOPin%d value=%d step=%d\n", i, val, step++);
    #endif
    if (bounce[i].update()) {
      val = bounce[i].read();
      #ifdef DEBUG_MODE  
      Serial.printf("bounce(%d).changed value=%d\n", i, val);
      #endif
      // Если значение датчика стало ЗАМКНУТО
      if (val == LOW) 
        sendData2Web(GPIOPin[i]);
    }
  }
  // Выключим светодиод после задержки, если он был включен
  turnOffLed(DELAY);
}
