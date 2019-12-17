$(eval OS := $(shell uname))
CFLAGS+=-std=c99 -g
LINK += -lpng

ifeq ($(OS),Darwin)
	LINK +=-lpthread -lm -lglfw3 -framework Cocoa -framework OpenGL -framework IOKit -framework CoreVideo
	#LINK += -lopencv_videoio
else
	LINK +=-lglfw -lGL -lX11 -lXi -lXrandr -lXxf86vm -lXinerama -lXcursor -lrt -lm -pthread -ldl
	CFLAGS += -D_XOPEN_SOURCE=500 -D_GNU_SOURCE -DGL_GLEXT_PROTOTYPES
endif

bin:
	mkdir $@

slicer: bin
	$(CC) $(CFLAGS) main.c -o bin/$@ $(LINK)

.PHONY: clean
clean:
	rm -rf bin
