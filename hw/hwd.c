#include <stdlib.h>
#include <stdio.h>

#include "gpio.h"
#include "camera.h"

#define CAM_WIDTH 1024
#define CAM_HEIGHT 768

typedef union {
	struct {
		uint8_t r, g, b;
	};
	uint8_t v[3];
} rgb_t;

typedef struct {
	rgb_t pixels[CAM_HEIGHT][CAM_WIDTH];
} frame_t;


int main (int argc, const char* argv[])
{
	cam_settings_t cam_cfg = { CAM_WIDTH, CAM_HEIGHT, 5 };
	cam_t cam = cam_open("/dev/video0", &cam_cfg);

	

	return 0;
}
