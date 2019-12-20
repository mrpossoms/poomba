#define GL_SILENCE_DEPRECATION

#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <pthread.h>
#include <sys/stat.h>
#include <dirent.h>
#include <stdbool.h>

#include <GLFW/glfw3.h>

#include "cli.h"
#include "png.h"


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
char* BASE_PATH = "/var/pood/ds";
char* SRC_DIR = "/var/pood/ds/src";
img_t CURRENT_IMG;
void* PIXELS = NULL;


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


void image_patch_rgba(rgb_t* dst, rgba_t* rgb, rectangle_t rect)
{
	// slice out patches to use for activation
	for (int kr = rect.h; kr--;)
	for (int kc = rect.w; kc--;)
	{
        rgba_t rgba = rgb[((rect.y + kr) * CURRENT_IMG.width) + rect.x + kc];
		rgb_t color = { rgba.r, rgba.g, rgba.b };
		dst[(kr * rect.w) + kc] = color;
	}
}


void image_patch_rgb(rgb_t* dst, rgb_t* rgb, rectangle_t rect)
{
    // slice out patches to use for activation
    for (int kr = rect.h; kr--;)
    for (int kc = rect.w; kc--;)
    {
        rgb_t color = rgb[((rect.y + kr) * CURRENT_IMG.width) + rect.x + kc];
        dst[(kr * rect.w) + kc] = color;
    }
}


void frame_to_canon(float x_frame, float y_frame, float* x, float* y)
{
    int w, h;
    float x_scale = 1, y_scale = 1;
    glfwGetFramebufferSize(WIN, &w, &h);
    // glfwGetWindowContentScale(WIN, &x_scale, &y_scale);

    *x = ((x_frame * x_scale / (float)w) - 0.5) * 2;
    *y = ((y_frame * y_scale / (float)h) - 0.5) * -2;
}


void frame_to_pix(float x_frame, float y_frame, int w_frame, int h_frame, int* x, int* y)
{
    int w, h;
    glfwGetFramebufferSize(WIN, &w, &h);

    *x = (x_frame / (float)w) * w_frame;
    *y = (y_frame / (float)h) * h_frame;
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
    struct dirent* dep = readdir(dp);
    for (; dep && (dep->d_type != DT_REG || dep->d_name[0] == '.'); dep = readdir(dp)) { }

    if (!dep)
    {
        closedir(dp);
        dp = NULL;
        return NULL;
    }

    return dep->d_name;
}

static void cursor_position_callback(GLFWwindow* window, double x, double y)
{
    if (glfwGetMouseButton(WIN, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS)
    {
        float ul[2];
        float lr[2];

        const int kernel_size = 64;
        frame_to_canon(x, y, ul + 0, ul + 1);
        frame_to_canon(x + kernel_size, y + kernel_size, lr + 0, lr + 1);

        rectangle_t patch_rec = { .w = kernel_size, .h = kernel_size };
        rgb_t patch[kernel_size * kernel_size];
        frame_to_pix(x, y, CURRENT_IMG.width, CURRENT_IMG.height, &patch_rec.x, &patch_rec.y);

        bool is_rgba = CURRENT_IMG.rgba_pixels != NULL;
        if (is_rgba)
        {
            image_patch_rgba(patch, PIXELS, patch_rec);
        }
        else
        {
            image_patch_rgb(patch, PIXELS, patch_rec);
        }


        char file_path[PATH_MAX] = {}, base_path[PATH_MAX] = {};
        sprintf(base_path, "%s/%d", BASE_PATH, LABEL_CLASS);
        mkdir(base_path, 0777);
        sprintf(file_path, "%s/%lx", base_path, random());

        write_png_file_rgb(file_path, patch_rec.w, patch_rec.h, (char*)patch);
    }
}

int main(int argc, char* argv[])
{
    cli_cmd_t cmds[] = {
        { 'c',
            .desc = "Specify class number for saving images",
            .set = &LABEL_CLASS,
            .type = ARG_TYP_INT,
            .opts = { .has_value = 1, .required = 1 },
        },
        { 'b',
            .desc = "Set base path",
            .set = &BASE_PATH,
            .type = ARG_TYP_STR,
            .opts = { .has_value = 1, .required = 1 },
        },
        { 's',
            .desc = "Set source image directory",
            .set = &SRC_DIR,
            .type = ARG_TYP_STR,
            .opts = { .has_value = 1, .required = 1 },
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

    glfwSetCursorPosCallback(WIN, cursor_position_callback);

    srandom(time(NULL));
    glfwMakeContextCurrent(WIN);
    setup_gl();
    create_texture(&frameTex);

    int space_last_state = GLFW_PRESS;

    while(!glfwWindowShouldClose(WIN)){
        bool is_rgba = CURRENT_IMG.rgba_pixels != NULL;
        PIXELS = is_rgba ? (void*)CURRENT_IMG.rgba_pixels : (void*)CURRENT_IMG.rgb_pixels;

        if (CURRENT_IMG.valid)
        {
            glTexImage2D(
                GL_TEXTURE_2D,
                0,
                is_rgba ? GL_RGBA : GL_RGB,
                CURRENT_IMG.width,
                CURRENT_IMG.height,
                0,
                is_rgba ? GL_RGBA : GL_RGB,
                GL_UNSIGNED_BYTE,
                PIXELS
            );
            glfwSetWindowSize(WIN, CURRENT_IMG.width, CURRENT_IMG.height);

            int w, h;
            glfwGetFramebufferSize(WIN, &w, &h);
            glViewport(0, 0, w, h);
        }

        int space_state = glfwGetKey(WIN, GLFW_KEY_SPACE);
        if (space_state == GLFW_RELEASE && space_state != space_last_state)
        {
            char path[PATH_MAX];
            const char* img_name = get_next_src_file(SRC_DIR);

            if (img_name)
            {
                sprintf(path, "%s/%s", SRC_DIR, img_name);
                CURRENT_IMG = read_png_file_rgb(path);
            }
        }
        space_last_state = space_state;


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

                const int kernel_size = 64;
                frame_to_canon(x, y, ul + 0, ul + 1);
                frame_to_canon(x + kernel_size, y + kernel_size, lr + 0, lr + 1);


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
