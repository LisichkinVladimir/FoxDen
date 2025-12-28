#include <inttypes.h>

#include "main.h"
#include "buffer.h"
#include "Bounce2.h"
#include "pulse_led.h"
#include "rest_api.h"
#include "bluetooth.h"
#include "preference.h"

// Пины к которым подключены устройства
static uint8_t GPIOPin[PIN_COUNT] = {0, 1};
// Bounce объект для счетчика, помогающий избежать закрытии или открытии множества нежелательных ложных состояний (похожих на шум)
Bounce bounce[PIN_COUNT] = {};

void setup() {
  #ifdef DEBUG_MODE
  Serial.begin(115200);
  delay(1500);
  Serial.println("Setup-----------------------------------");
  Serial.printf("Модель чипа: %s\n", ESP.getChipModel());
  Serial.printf("Ревизия чипа: %u\n", ESP.getChipRevision());
  Serial.printf("Версия SDK: %s\n", ESP.getSdkVersion());
  #endif
  // Инициализируем переменные из Flash-памяти
  initPreference();
  #ifdef DEBUG_MODE
  // Инициализируем светодиод
  initLed();
  #endif
  // Инициализируем буферы
  initBuffer();
  // Инициализируем Bluetooth
  initBluetooth();
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
    #ifdef DEBUG_MODE_MAIN
    static int step = 0;
    Serial.printf("GPIOPin%d value=%d step=%d\n", i, val, step++);
    if (step == 1000)
      step = 0;
    #endif
    if (bounce[i].update()) {
      val = bounce[i].read();
      #ifdef DEBUG_MODE  
      Serial.printf("bounce(%d).changed value=%d\n", i, val);
      #endif
      // Если значение датчика стало ЗАМКНУТО
      if (val == LOW) 
        putData2Buffer(GPIOPin[i]);
    }
  }

  /*char* mac_address = NULL;
  tm* timeinfo = NULL;
  unsigned long* synchTime = NULL;
  if (initWeb(&mac_address, &timeinfo, &synchTime)) {
    Pulse p = {millis(), 0};
    std::vector<Pulse> pulseArray;
    if (connect2Web(mac_address)) {
      pulseArray.push_back(p);
      sendData2Web(mac_address, timeinfo, synchTime, pulseArray);
    }
    Serial.print("NEW loop\n");
  }*/

  //checkBluetoothConnected();
}
