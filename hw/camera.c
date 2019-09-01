#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <string.h>
#include <strings.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <assert.h>

#include "camera.h"


cam_t cam_open(const char* path, cam_settings_t* cfg)
{
#ifndef __linux__
	const size_t frame_size = cfg->width * cfg->height * 3;
	void** frame_buffer_ptrs = (void**)malloc(sizeof(void*) * 2);
	uint8_t* frame_buffer = (uint8_t*)malloc(frame_size * 2);
	frame_buffer_ptrs[0] = frame_buffer;
	frame_buffer_ptrs[1] = frame_buffer + frame_size;
	cam_t dummy = {
		.frame_buffers = frame_buffer_ptrs,
	};
	return dummy;
#else
	int fd = open(path, O_RDWR);
	int res = 0;

	if(fd < 0)
	{
		printf("Error opening video device '%s'", path);
		//exit(-1);

		cam_t empty = {};
		return empty;
	}

	struct v4l2_capability cap;
	res = ioctl(fd, VIDIOC_QUERYCAP, &cap);
	if(res < 0)
	{
		printf("Error: %d querying '%s' for capabilities (%d)", res, path, errno);
		exit(-2);
	}

	if(!(cap.capabilities & V4L2_CAP_VIDEO_CAPTURE))
	{
		printf("Error: '%s' lacks V4L2_CAP_VIDEO_CAPTURE capability", path);
	}

	res = cam_config(fd, cfg);
	if(res < 0)
	{
		printf("Error: %d configuring '%s' (%d)", res, path, errno);
		exit(-3);
	}

	// Inform v4l about the buffers we want to receive data through
	struct v4l2_requestbuffers bufrequest = {};
	bufrequest.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	bufrequest.memory = V4L2_MEMORY_MMAP;
	bufrequest.count = 2;

	if(ioctl(fd, VIDIOC_REQBUFS, &bufrequest) < 0)
	{
		printf("VIDIOC_REQBUFS");
		exit(-4);
	}


	if(bufrequest.count < 2)
	{
		printf("Not enough memory");
		exit(-5);
	}


	struct v4l2_buffer bufferinfo = {};
	void** fbs = calloc(sizeof(void*), bufrequest.count);
	for(int i = bufrequest.count; i--;)
	{
		bufferinfo.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
		bufferinfo.memory = V4L2_MEMORY_MMAP;
		bufferinfo.index = i;

		if(ioctl(fd, VIDIOC_QUERYBUF, &bufferinfo) < 0)
		{
			printf("VIDIOC_QUERYBUF");
			exit(-5);
		}

		fbs[i] = mmap(
			NULL,
			bufferinfo.length,
			PROT_READ | PROT_WRITE,
			MAP_SHARED,
			fd,
			bufferinfo.m.offset
		);

		if(fbs[i] == MAP_FAILED)
		{
			printf("mmap failed");
			exit(-6);
		}

		bzero(fbs[i], bufferinfo.length);

		res = ioctl(fd, VIDIOC_QBUF, &bufferinfo);

		if (res) printf("cam_open(): VIDIOC_QBUF");
	}


	cam_t cam = {
		.fd = fd,
		.frame_buffers = fbs,
		.buffer_info = bufferinfo,
	};

	cam_wait_frame(&cam);

	int type = bufferinfo.type;
	if(ioctl(fd, VIDIOC_STREAMON, &type) < 0)
	{
		printf("Error starting streaming");
		exit(-7);
	}

	return cam;
#endif
}


int cam_request_frame(cam_t* cam)
{
#ifndef __linux__
	return 0;
#else
	cam->buffer_info.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	cam->buffer_info.memory = V4L2_MEMORY_MMAP;

	return ioctl(cam->fd, VIDIOC_QBUF, &cam->buffer_info);
#endif
}


int cam_wait_frame(cam_t* cam)
{
#ifndef __linux__
	return 0;
#else
	int res = ioctl(cam->fd, VIDIOC_DQBUF, &cam->buffer_info);

	if (res != 0) printf("cam_wait_frame(): VIDIOC_DQBUF");

	switch(res)
	{
		case EAGAIN:
			printf("EAGAIN");
			break;
		case EINVAL:
			printf("EINVAL");
			break;
		case EIO:
			printf("EIO");
			break;

	}

	return res;
#endif
}


int cam_config(int fd, cam_settings_t* cfg)
{
#ifndef __linux__
	return 0;
#else
	struct v4l2_format format;

	if(!cfg)
	{
		printf("Error: null configuration provided");
		return -1;
	}

	format.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	format.fmt.pix.pixelformat = V4L2_PIX_FMT_RGB24;
	format.fmt.pix.width = cfg->width;
	format.fmt.pix.height = cfg->height;

	if(ioctl(fd, VIDIOC_S_FMT, &format) < 0)
	{
		printf("Error: failed applying camera settings");
		return -3;
	}

	struct v4l2_streamparm parm = {};

	parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;

	parm.parm.capture.timeperframe.numerator = 1;
	parm.parm.capture.timeperframe.denominator = cfg->frame_rate;

	return ioctl(fd, VIDIOC_S_PARM, &parm);
#endif
}
