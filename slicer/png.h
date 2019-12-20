#include <png.h>

typedef union {
    struct {
        uint8_t r, g, b;
    };
    uint8_t v[3];
} rgb_t;

typedef union {
    struct {
        uint8_t r, g, b, a;
    };
    uint8_t v[4];
} rgba_t;

typedef struct {
    bool valid;
    size_t width, height;
    rgb_t* rgb_pixels;
    rgba_t* rgba_pixels;
} img_t;

int write_png_file_rgb(
    const char* path,
    int width,
    int height,
    const char* buffer){

    FILE *fp = fopen(path, "wb");

    if(!fp)
    {
        fprintf(stderr, "Couldn't open %s for writing\n", path);
        return -1;
    }

    png_structp png = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    if (!png) return -2;

    png_infop info = png_create_info_struct(png);
    if (!info) return -3;

    if (setjmp(png_jmpbuf(png))) return -4;

    png_init_io(png, fp);

    // Output is 8bit depth, RGB format.
    png_set_IHDR(
        png,
        info,
        width, height,
        8,
        PNG_COLOR_TYPE_RGB,
        PNG_INTERLACE_NONE,
        PNG_COMPRESSION_TYPE_DEFAULT,
        PNG_FILTER_TYPE_DEFAULT
    );
    png_write_info(png, info);

    png_bytep rows[height];
    for(int i = height; i--;)
    {
        rows[i] = (png_bytep)(buffer + i * (width * 3));
    }

    png_write_image(png, rows);
    png_write_end(png, NULL);

    fclose(fp);

    return 0;
}

img_t read_png_file_rgb(const char* path)
{
    img_t img = {};

    char header[8];    // 8 is the maximum size that can be checked
    png_structp png_ptr = NULL;
    png_infop info_ptr;
    png_bytep* row_pointers;
    png_byte color_type;

    fprintf(stderr, "loading texture '%s'\n", path);

    /* open file and test for it being a png */
    FILE *fp = fopen(path, "rb");
    if (!fp)
    {
        fprintf(stderr, "[read_png_file] File %s could not be opened for reading", path);
        return img;
    }

    fread(header, 1, 8, fp);
    if (png_sig_cmp((const char*)header, 0, 8))
    {
        fprintf(stderr, "[read_png_file] File %s is not recognized as a PNG file", path);
        return img;
    }

    /* initialize stuff */
    png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);

    if (!png_ptr)
    {
        fprintf(stderr, "[read_png_file] png_create_read_struct failed");
        return img;
    }

    info_ptr = png_create_info_struct(png_ptr);
    if (!info_ptr)
    {
        fprintf(stderr, "[read_png_file] png_create_info_struct failed");
        return img;
    }

    if (setjmp(png_jmpbuf(png_ptr)))
    {
        fprintf(stderr, "[read_png_file] Error during init_io");
        return img;
    }

    png_init_io(png_ptr, fp);
    png_set_sig_bytes(png_ptr, 8);

    png_read_info(png_ptr, info_ptr);

    img.width = png_get_image_width(png_ptr, info_ptr);
    img.height = png_get_image_height(png_ptr, info_ptr);
    color_type = png_get_color_type(png_ptr, info_ptr);

    png_read_update_info(png_ptr, info_ptr);

    /* read file */
    if (setjmp(png_jmpbuf(png_ptr)))
    {
        fprintf(stderr, "[read_png_file] Error during read_image");
        return img;
    }

    int depth = 0;
    uint8_t* pixel_buf = NULL;

    switch (color_type) {
        case PNG_COLOR_TYPE_RGBA:
            depth = 4;
            img.rgba_pixels = (rgba_t*)calloc(img.width * img.height, sizeof(rgba_t));
            pixel_buf = (uint8_t*)img.rgba_pixels;
            break;
        case PNG_COLOR_TYPE_PALETTE:
        case PNG_COLOR_TYPE_RGB:
            depth = 3;
            img.rgb_pixels = (rgb_t*)calloc(img.width * img.height, sizeof(rgb_t));
            pixel_buf = (uint8_t*)img.rgb_pixels;
            break;
    }

    row_pointers = (png_bytep*) malloc(sizeof(png_bytep) * img.height);

    for (int y = 0; y < img.height; y++)
    {
        row_pointers[y] = (png_byte*) malloc(png_get_rowbytes(png_ptr, info_ptr));
        assert(row_pointers[y]);
    }

    png_read_image(png_ptr, row_pointers);

    int bytes_per_row = png_get_rowbytes(png_ptr, info_ptr);
    for (int y = 0; y < img.height; y++)
    {
        memcpy(pixel_buf + (y * bytes_per_row), row_pointers[y], bytes_per_row);
        free(row_pointers[y]);
    }
    free(row_pointers);
    fclose(fp);
    fprintf(stderr, "OK\n");

    img.valid = true;

    return img;
}
