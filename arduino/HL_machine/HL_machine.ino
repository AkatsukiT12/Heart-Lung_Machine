/* Heart-Lung machine prototype (educational) 
   - Bubble detection: LDR (A0) + LED (D11)
   - SPO2 proxy: LDR (A1) + LED (D10)
   - Pump control via H-bridge: D5 (PWM), D8, D9
   - Suction pump via MOSFET: D6 (PWM)
   - Pulse sensor: A2
   - Flowmeter: D3 (interrupt)
   - Temperature: DS18B20 on D2 (OneWire)
   - LCD: I2C (A4/A5)
   - Alarm: buzzer D12, alarm LED D13
   NOTE: For educational use ONLY (not clinical).
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ---------- PIN DEFINITIONS ----------
const int pulseSensorPin = A2;
const int bubbleLdrPin   = A0;
const int spo2LdrPin     = A1;

const int bubbleLedPin   = 11;
const int spo2LedPin     = 10;

const int oneWirePin     = 2;   // DS18B20
const int flowMeterPin   = 3;   // interrupt pin for pulses

const int pumpPWMPin     = 5;   // ENA (PWM)
const int pumpDir1Pin    = 8;   // IN1
const int pumpDir2Pin    = 9;   // IN2

const int suctionPWMPin  = 6;   // MOSFET gate

const int buzzerPin      = 12;
const int alarmLedPin    = 13;

// ---------- SENSORS & LCD ----------
LiquidCrystal_I2C lcd(0x27, 16, 2);
OneWire oneWire(oneWirePin);
DallasTemperature sensors(&oneWire);

// ---------- Pulse sensor ----------
float heartRate = 0.0;

// ---------- Rolling windows ----------
const int windowSize = 8;
float pressureHrWindow[windowSize];
int pressureWindowIndex = 0;
bool windowFilled = false;

// ---------- Calibration constants ----------
float k_hr_to_pressure = 0.3;
float safePressureMin = 40.0;
float safePressureMax = 140.0;

// ---------- Thresholds ----------
int bubbleThreshold = 300;
int spo2Threshold   = 350;
float tempLow  = 35.5;
float tempHigh = 38.5;
bool alarmState = false;

// ---------- Tolerance system ----------
unsigned long systemStartTime = 0;
const unsigned long primingTime = 5000;  // First 5 seconds ignore bubble/spo2 alarms
int bubbleBadCount = 0;
int spo2BadCount = 0;
const int toleranceCount = 5; // Requires 5 consecutive bad readings

// ---------- Timing ----------
unsigned long lastDisplayMillis = 0;
const unsigned long displayInterval = 500;

// ---------- Debug control ----------
const bool DEBUG_SERIAL = true;

// ---------- Function prototypes ----------
void checkPulseSensor();
void triggerAlarm(const char *reason);
float computeStdDev(float arr[], int n, float mean);

// ---------- Setup ----------
void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  pinMode(bubbleLedPin, OUTPUT);
  pinMode(spo2LedPin, OUTPUT);
  pinMode(pumpPWMPin, OUTPUT);
  pinMode(pumpDir1Pin, OUTPUT);
  pinMode(pumpDir2Pin, OUTPUT);
  pinMode(suctionPWMPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);
  pinMode(alarmLedPin, OUTPUT);

  digitalWrite(bubbleLedPin, HIGH);
  digitalWrite(spo2LedPin, HIGH);

  lcd.init();
  lcd.backlight();
  sensors.begin();

  systemStartTime = millis();

  for (int i = 0; i < windowSize; i++) {
    pressureHrWindow[i] = 0;
  }

  // Initial pump state: always running
  analogWrite(pumpPWMPin, 150);
  digitalWrite(pumpDir1Pin, HIGH);
  digitalWrite(pumpDir2Pin, LOW);
  analogWrite(suctionPWMPin, 120);

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("HL Machine Demo");
  lcd.setCursor(0,1);
  lcd.print("Educational Only");
  delay(1200);

  if (DEBUG_SERIAL) Serial.println("System startup complete");
}

// ---------- Loop ----------
void loop() {
  unsigned long now = millis();

  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);

  int bubbleValue = analogRead(bubbleLdrPin);
  int spo2Value   = analogRead(spo2LdrPin);

  checkPulseSensor(); // updates heartRate

  // Pressure estimate based only on HR
  float p_hr = k_hr_to_pressure * heartRate;

  // Rolling window
  pressureHrWindow[pressureWindowIndex] = p_hr;
  pressureWindowIndex++;
  if (pressureWindowIndex >= windowSize) {
    pressureWindowIndex = 0;
    windowFilled = true;
  }

  int usedWindowLen = windowFilled ? windowSize : pressureWindowIndex;

  float meanHr = 0;
  for (int i = 0; i < usedWindowLen; i++) meanHr += pressureHrWindow[i];
  if (usedWindowLen > 0) meanHr /= usedWindowLen;

  float stdHr = computeStdDev(pressureHrWindow, usedWindowLen, meanHr);

  float chosenPressure = meanHr;

  // Safety checks
  bool bubbleDetected = (bubbleValue < bubbleThreshold);
  bool spo2Bad        = (spo2Value < spo2Threshold);
  bool tempBad        = (tempC < tempLow || tempC > tempHigh);
  bool pressureBad    = (chosenPressure < safePressureMin || chosenPressure > safePressureMax);

  // SPO2 & BUBBLE TOLERANCE LOGIC
  bool priming = (millis() - systemStartTime < primingTime);

  if (!priming) {
    if (bubbleDetected) {
      bubbleBadCount++;
      if (bubbleBadCount >= toleranceCount) triggerAlarm("BUBBLE");
      if (DEBUG_SERIAL) {
        Serial.print("[BUBBLE] count="); Serial.println(bubbleBadCount);
      }
    } else bubbleBadCount = 0;

    if (spo2Bad) {
      spo2BadCount++;
      if (spo2BadCount >= toleranceCount) triggerAlarm("SPO2_LOW");
      if (DEBUG_SERIAL) {
        Serial.print("[SPO2] count="); Serial.println(spo2BadCount);
      }
    } else spo2BadCount = 0;

  } else {
    bubbleBadCount = 0;
    spo2BadCount = 0;
    if (DEBUG_SERIAL) Serial.print("[PRIMING]...");
  }

  // Temperature & pressure alarms
  if (tempBad) triggerAlarm("TEMP");
  if (pressureBad) triggerAlarm("PRESSURE");

  // --- PUMPS ALWAYS RUN ---
  analogWrite(pumpPWMPin, 150);
  digitalWrite(pumpDir1Pin, HIGH);
  digitalWrite(pumpDir2Pin, LOW);
  analogWrite(suctionPWMPin, 120);

  // LCD & Serial debug update
  if (now - lastDisplayMillis >= displayInterval) {
    lastDisplayMillis = now;

    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("HR:");
    lcd.print((int)heartRate);
    lcd.print(" P:");
    lcd.print(chosenPressure,0);

    lcd.setCursor(0,1);
    lcd.print("B:");
    lcd.print(bubbleValue);
    lcd.print(" S:");
    lcd.print(spo2Value);
    lcd.print(" T:");
    if (tempC == DEVICE_DISCONNECTED_C) lcd.print("Err");
    else lcd.print(tempC,1);

    if (DEBUG_SERIAL) {
      Serial.print("[STATUS] HR=");
      Serial.print(heartRate,1);
      Serial.print(" P=");
      Serial.print(chosenPressure,1);
      Serial.print(" Bval=");
      Serial.print(bubbleValue);
      Serial.print(" Sval=");
      Serial.print(spo2Value);
      Serial.print(" T=");
      Serial.print(tempC);
      Serial.print(" Alarm=");
      Serial.println(alarmState ? "YES" : "NO");
    }
  }

  delay(10);
}

// ---------- Pulse sensor ----------
void checkPulseSensor() {
  static bool wasAbove = false;
  static unsigned long lastBeatMillisLocal = 0;

  int val = analogRead(pulseSensorPin);
  unsigned long t = millis();

  int threshold = 550;
  if (val > threshold && !wasAbove) {
    unsigned long interval = t - lastBeatMillisLocal;
    lastBeatMillisLocal = t;

    if (interval > 250 && interval < 2000) {
      float instantBPM = 60000.0 / (float)interval;
      static float bpmAvg = 0;
      if (bpmAvg == 0) bpmAvg = instantBPM;
      bpmAvg = (bpmAvg * 0.7) + (instantBPM * 0.3);
      heartRate = bpmAvg;
      if (DEBUG_SERIAL) {
        Serial.print("[PULSE] BPM="); Serial.println(heartRate,1);
      }
    }
    wasAbove = true;
  }
  else if (val < threshold) {
    wasAbove = false;
  }
}

// ---------- Alarm ----------
void triggerAlarm(const char *reason) {
  alarmState = true;
  digitalWrite(alarmLedPin, HIGH);
  tone(buzzerPin, 2000, 100);
  Serial.print("ALARM: ");
  Serial.println(reason);
}

// ---------- StdDev ----------
float computeStdDev(float arr[], int n, float mean) {
  if (n <= 1) return 0.0;
  float s = 0.0;
  for (int i = 0; i < n; i++) {
    float d = arr[i] - mean;
    s += d*d;
  }
  return sqrt(s / (float)(n - 1));
}