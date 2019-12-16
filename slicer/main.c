#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <pthread.h>
#include <dirent.h>

#include <GLFW/glfw3.h>

#include "cli.h"
#include "png.h"

#define GL_SILENCE_DEPRECATION 1
// #define RENDER_DEMO

#ifdef __linux__
#define WIN_W (640)
#define WIN_H (480)
#else
#define WIN_W (640 >> 1)
#define WIN_H (480 >> 1)
#endif

typedef struct {
    int x, y, w, h;
} rectangle_t;

GLFWwindow* WIN;
GLuint frameTex;
int LABEL_CLASS;
char* BASE_PATH;
char* SRC_DIR = "/var/pood/ds/src";
img_t* CURRENT_IMG;


static void setup_gl()
{
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glEnable(GL_TEXTURE_2D);
    glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL);
}


static void create_texture(GLuint* tex)
{
    glGenTextures(1, tex);
    glBindTexture(GL_TEXTURE_2D, *tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
}


void image_patch_b(color_t* dst, color_t* rgb, rectangle_t rect)
{	
	// slice out patches to use for activation
	for (int kr = rect.h; kr--;)
	for (int kc = rect.w; kc--;)
	{
		color_t color = rgb[((rect.y + kr) * FRAME_W) + rect.x + kc];
		dst[(kr * rect.w) + kc] = color;
	}
}


void frame_to_canon(float x_frame, float y_frame, float* x, float* y)
{
    *x = ((x_frame / (float)WIN_W) - 0.5) * 2;
    *y = ((y_frame / (float)WIN_H) - 0.5) * -2;
}


void frame_to_pix(float x_frame, float y_frame, int w_frame, int h_frame, int* x, int* y)
{
    *x = (x_frame / (float)WIN_W) * w_frame;
    *y = (y_frame / (float)WIN_H) * h_frame;
}

const char* get_next_src_file(const char* src_dir)
{
    static DIR* dp;

    if (!dp)
    {
        dp = opendir(src_dir);
        if (!dp) { return NULL; }
    }

    // read next, skip all non-regular files
    static struct dirent* dep = NULL;
    for (; dep && dep->d_type != DT_REG; dep = readdir(dp)) { }

    if (!dep)
    {
        closedir(dp);
        dp = NULL;
        return NULL;
    }

    return dep->d_name;
}

int main(int argc, char* argv[])
{
    cli_cmd_t cmds[] = {
        { 'c',
            .desc = "Specify class number for saving images",
            .set = &LABEL_CLASS,
            .type = ARG_TYP_INT,
            .opts = { .has_value = 1 },
        },
        { 'p',
            .desc = "Set base path",
            .set = &BASE_PATH,
            .type = ARG_TYP_STR,
            .opts = { .has_value = 1 },
        },
        {}
    };
    const char* prog_desc = "";

    if (cli(prog_desc, cmds, argc, argv))
    {
        return -2;
    }

    if (!glfwInit()) { return -1; }

    WIN = glfwCreateWindow(WIN_W, WIN_H, "slicer", NULL, NULL);

    if (!WIN){
        glfwTerminate();
        return -2;
    }

    srandom(time(NULL));
    glfwMakeContextCurrent(WIN);
    setup_gl();
    create_texture(&frameTex);

    img_t img;
    {
        char path[PATH_MAX];
        const char* img_name = get_next_src_file(SRC_DIR);

        if (img_name)
        {
            snprintf(path, "%s/%s", SRC_DIR, img_name);
            CURRENT_IMG = read_png_file_rgb(path);
        }
    }


    while(!glfwWindowShouldClose(WIN)){
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            CURRENT_IMG->width,
            CURRENT_IMG->height,
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            (void*)CURRENT_IMG->pixels
        );

        int space_down = glfwGetKey(WIN, GLFW_KEY_SPACE) == GLFW_PRESS;

        glClear(GL_COLOR_BUFFER_BIT);
        glEnable(GL_TEXTURE_2D);

        glBegin(GL_QUADS);
            glTexCoord2f(1, 0);
            glVertex2f( 1,  1);

            glTexCoord2f(0, 0);
            glVertex2f(-1,  1);

            glTexCoord2f(0, 1);
            glVertex2f(-1, -1);

            glTexCoord2f(1, 1);
            glVertex2f( 1, -1);
        glEnd();

        if (BASE_PATH)
        {
            if (glfwGetMouseButton(WIN, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS)
            {
                double x, y;
                glfwGetCursorPos(WIN, &x, &y);

                float ul[2];
                float lr[2];

                frame_to_canon(x, y, ul + 0, ul + 1);
                frame_to_canon(x + 16, y + 16, lr + 0, lr + 1);

                rectangle_t patch_rec = { .w = 16, .h = 16 };
                color_t patch[16 * 16];
                frame_to_pix(x, y, &patch_rec.x, &patch_rec.y);
                image_patch_b(patch, rgb, patch_rec);

                char file_path[PATH_MAX] = {}, base_path[PATH_MAX] = {};
                snprintf(base_path, PATH_MAX, "%s/%d", BASE_PATH, LABEL_CLASS);
                mkdir(base_path, 0777);
                snprintf(file_path, PATH_MAX, "%s/%lx", base_path, random());
                write_png_file_rgb(file_path, patch_rec.w, patch_rec.h, (char*)patch);

                glBegin(GL_QUADS);
                    glColor4f(1, 0, 0, 0.5);
                    glVertex2f(ul[0], ul[1]);
                    glVertex2f(lr[0], ul[1]);
                    glVertex2f(lr[0], lr[1]);
                    glVertex2f(ul[0], lr[1]);
                glEnd();
            }
        }

        glfwPollEvents();
        glfwSwapBuffers(WIN);
    }

    return 0;
}
