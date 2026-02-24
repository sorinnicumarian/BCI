// Fixed Sampling at 512 Hz - BioAmp EXG Pill
// For use with predict.py

#define SAMPLE_RATE 512  // Changed from 125 to 512 Hz
#define BAUD_RATE 115200
#define INPUT_PIN A0


void setup() {
	// Serial connection begin
	Serial.begin(BAUD_RATE);
}

void loop() {
	// Calculate elapsed time
	static unsigned long past = 0;
	unsigned long present = micros();
	unsigned long interval = present - past;
	past = present;

	// Run timer
	static long timer = 0;
	timer -= interval;

	// Sample
	if(timer < 0){
		timer += 1000000 / SAMPLE_RATE;
		int sensor_value = analogRead(INPUT_PIN);
		Serial.println(sensor_value);
	}
}
