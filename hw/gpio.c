#include "gpio.h"

#include <sys/stat.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

static int path_exists(const char* path)
{
	struct stat statbuf;

	switch (stat(path, &statbuf))
	{
		case 0:      return 1;
		case ENOENT: return 0;
	}

	return 0;
}


int hwd_gpio_set(int pin, int state)
{
	char buf[PATH_MAX] = {};
	snprintf(buf, sizeof(buf), "/sys/class/gpio/gpio%d", pin);

	if (!path_exists(buf))
	{
		snprintf(buf, sizeof(buf), "echo %d > /sys/class/gpio/export", pin);
		system(buf);

		snprintf(buf, sizeof(buf), "echo out > /sys/class/gpio/gpio%d/direction", pin);
		system(buf);
	}
		
	snprintf(buf, sizeof(buf), "echo %d > /sys/class/gpio/gpio%d/value", state, pin);

	return 0;
}
