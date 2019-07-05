#ifndef HWD_CAMERA_H
#define HWD_CAMERA_H

#include <time.h>

#ifdef __linux__
#include <linux/videodev2.h>
#include <inttypes.h>
#include <sys/types.h>
#endif

#define GET_CHROMA_FROM_VIEW(view, r, c) (view).chroma[((r) * FRAME_W >> 1) + ((r) >> 1)]

typedef struct {
	int width, height;
	int frame_rate;	
} cam_settings_t;

typedef struct {
	int fd;
	void** frame_buffers;
#ifdef __linux__
	struct v4l2_buffer buffer_info;
#endif
} cam_t;

// Set when cam_config is called
extern size_t CAM_BYTES_PER_FRAME;

int   cam_config(int fd, cam_settings_t* cfg);
cam_t cam_open(const char* path, cam_settings_t* cfg);

int cam_request_frame(cam_t* cam);
int cam_wait_frame(cam_t* cam);

#endif
