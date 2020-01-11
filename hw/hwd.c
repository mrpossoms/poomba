#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <netdb.h>
#include <fcntl.h>
#include <strings.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>

#include "gpio.h"
#include "camera.h"

#define BLUR_THRESHOLD 0
#define MIN_IMG_DIFF 2
#define CAM_WIDTH (640 >> 0)
#define CAM_HEIGHT (480 >> 0)
#define DS_WIDTH  (640 >> 1)
#define DS_HEIGHT (480 >> 1)

#define EACH_ROW_COL(_R, _C) for (int r = 0; r < _R; ++r) \
                             for (int c = 0; c < _C; ++c) \

typedef struct { size_t r, c; } dims_t;

typedef union {
	struct {
		uint8_t r, g, b;
	};
	uint8_t v[3];
} rgb_t;

typedef struct {
	rgb_t pixels[CAM_HEIGHT][CAM_WIDTH];
} frame_t;

typedef struct {
	rgb_t pixels[DS_HEIGHT][DS_WIDTH];
} ds_frame_t;

typedef struct {
	char magic[4];
	int32_t width, height, depth;
} hdr_t;


int request_classification(const char* host_name, ds_frame_t* frame, uint32_t* is_ok)
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
		.width = DS_WIDTH,
		.height = DS_HEIGHT >> 2, // we will only send the bottom half of the frame
		.depth = 3,
	};
	if (write(sock, &hdr, sizeof(hdr_t)) != sizeof(hdr_t)) { res = -3; goto abort; }

	// send the frame
	size_t to_write = sizeof(ds_frame_t) >> 2;
	uint8_t* buf = ((uint8_t*)frame);

	for (size_t written = 0; written < to_write;)
	{
		int bytes = write(sock, buf + written, to_write - written);

		if (bytes < 0)
		{
			res = -4;
			goto abort;
		}

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


float variance(float mu, const int* v, size_t n)
{
	float var = 0;
	for (size_t i = 0; i < n; ++i)
	{
		int d = v[i] - mu;
		var += d * d;
	}
	return var / (n - 1);
}


void leplacian(ds_frame_t* frame, int* L, float* mu, dims_t dims)
{
	const int K[3][3] = {
		{ 0, 1, 0 },
		{ 1,-4, 1 },
		{ 0, 1, 0 },
	};

	*mu = 0;

	size_t l_c = dims.c - 2;
	size_t l_r = dims.r - 2;

	for (int r = 0; r < l_r; ++r)
	for (int c = 0; c < l_c; ++c)
	{
		int inner = 0;
		for (int k_r = 0; k_r < 3; k_r++)
		for (int k_c = 0; k_c < 3; k_c++)
		{
			rgb_t rgb = frame->pixels[r+k_r][c+k_c];
			inner += K[k_r][k_c] * rgb.r;//(rgb.r + rgb.g + rgb.b) / 3;
		}

		L[r * l_c + c] = inner;

		*mu += inner;
	}

	*mu /= (l_c * l_r);
}


void get_frame(cam_t const* cam, frame_t* frame)
{
#ifndef __linux__
	static int rand_fd;
	if (rand_fd == 0)
	{
		rand_fd = open("/dev/random", O_RDONLY);
	}

	read(rand_fd, frame, sizeof(frame_t));
#else
	int bi = cam->buffer_info.index;
	memcpy(frame, cam->frame_buffers[bi], sizeof(frame_t));
#endif
}


unsigned int frame_diff(frame_t* f0, frame_t* f1)
{
	unsigned int diff = 0;

	EACH_ROW_COL(CAM_HEIGHT, CAM_WIDTH)
	{
		diff += abs(f0->pixels[r][c].r - f1->pixels[r][c].r);
	}

	return diff / (CAM_WIDTH * CAM_HEIGHT);
}


void downsample_frame(ds_frame_t* ds_frame, frame_t* frame)
{
	int dr = CAM_HEIGHT / DS_HEIGHT;
	int dc = CAM_WIDTH / DS_WIDTH;

	EACH_ROW_COL(DS_HEIGHT, DS_WIDTH)
	{
		ds_frame->pixels[r][c] = frame->pixels[r * dr][c * dc];
	}
}


int main (int argc, const char* argv[])
{
	if (NULL == argv[1])
	{
		fprintf(stderr, "Please provide IP address to pood server\n");
		exit(1);
	}

	cam_settings_t cam_cfg = { CAM_WIDTH, CAM_HEIGHT, 30 };
	cam_t cam = cam_open("/dev/video0", &cam_cfg);
	frame_t frames[2];

	int L[DS_HEIGHT - 2][DS_WIDTH - 2];

	for (unsigned int i = 0; 1; ++i)
	{
		int frame_idx = i % 2;
		cam_request_frame(&cam);
		cam_wait_frame(&cam);
		get_frame(&cam, frames + frame_idx);

		int diff = frame_diff(frames + 0, frames + 1);
		//fprintf(stderr, "frame_diff: %d\n", diff);
		if (diff < MIN_IMG_DIFF) { continue; }

		uint32_t is_ok = 0;
		float mu = 0;
		frame_t* current_frame = frames + frame_idx;
		ds_frame_t ds_frame;

		downsample_frame(&ds_frame, current_frame);
		leplacian(&ds_frame, (int*)L, &mu, (dims_t){ DS_HEIGHT, DS_WIDTH });
		int var = variance(mu, (int*)L, sizeof(L) / sizeof(int));
		printf("mu: %f, variance: %d\n", mu, var);

		if (var < BLUR_THRESHOLD)
		{

		}

		request_classification(argv[1], &ds_frame, &is_ok);
		hwd_gpio_set(4, is_ok);
	}

	return 0;
}
