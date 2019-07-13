#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <netdb.h>
#include <strings.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>

#include "gpio.h"
#include "camera.h"

#define CAM_WIDTH 640
#define CAM_HEIGHT 480

typedef union {
	struct {
		uint8_t r, g, b;
	};
	uint8_t v[3];
} rgb_t __attribute__ ((packed));

typedef struct {
	rgb_t pixels[CAM_HEIGHT][CAM_WIDTH];
} frame_t __attribute__ ((packed));

typedef struct {
	char magic[4];
	int32_t width, height, depth;
} hdr_t __attribute__ ((packed));

int request_classification(const char* host_name, frame_t* frame, uint32_t* is_ok)
{
	int sock = socket(AF_INET, SOCK_STREAM, 0);
	int res = 0;
	if (sock < 0) { res = -1; goto abort; }

	struct hostent* host = gethostbyname(host_name);
	if (host == NULL) { res = -2; goto abort; }

	// fill in host_addr with resolved info
	struct sockaddr_in host_addr = {};
	bcopy(
		(char *)host->h_addr,
		(char *)&host_addr.sin_addr.s_addr,
		host->h_length
	);
	host_addr.sin_port   = htons(1337);
	host_addr.sin_family = AF_INET;

	res = connect(sock, (struct sockaddr*)&host_addr, sizeof(host_addr));
	if (res < 0) { goto abort; }

	// send the header
	hdr_t hdr = {
		.magic = "POOP",
		.width = CAM_WIDTH,
		.height = CAM_HEIGHT,
		.depth = 3,
	};
	if (write(sock, &hdr, sizeof(hdr_t)) != sizeof(hdr_t)) { res = -3; goto abort; }

	// send the frame
	for (size_t written = 0; written < sizeof(frame_t);)
	{
		int bytes = write(sock, frame + written, sizeof(frame_t) - written);
		
		if (bytes < 0)
		{ res = -4; goto abort; }

		written += bytes;
	}

	// wait, and read back the classification
	if (read(sock, is_ok, sizeof(uint32_t)) != sizeof(uint32_t))
	{
		res = -6; goto abort;
	}

abort:
	if (res) { fprintf(stderr, "error %d: %s\n", res, strerror(errno)); }
	close(sock);
	return res;
}


void get_frame(cam_t const* cam, frame_t* frame)
{
	int bi = cam->buffer_info.index;
	memcpy(frame, cam->frame_buffers[bi], sizeof(frame_t));
}


int main (int argc, const char* argv[])
{
	cam_settings_t cam_cfg = { CAM_WIDTH, CAM_HEIGHT, 5 };
	cam_t cam = cam_open("/dev/video0", &cam_cfg);
	frame_t last_frame;

	while(1)
	{
		cam_request_frame(&cam);
		cam_wait_frame(&cam);
		get_frame(&cam, &last_frame);

		uint32_t is_ok = 0;
		request_classification(argv[1], &last_frame, &is_ok);
		hwd_gpio_set(4, is_ok);
	}

	return 0;
}
