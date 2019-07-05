CFLAGS=-g
SRCS=$(shell ls *.c)
OBJS=$(addprefix obj/,$(SRCS:.c=.o))

.PHONY: what
what:
	@echo $(OBJS)

bin:
	mkdir bin

obj: bin
	mkdir -p obj

.PHONY: %.c
%.c:
	@echo "Building $@"

obj/%.o: %.c obj
	$(CC) $(CFLAGS) -c $< -o $@

hwd: $(OBJS)
	@echo $(OBJS)
	$(CC) $(CFLAGS) $^ -o bin/$@
	
.PHONY: clean
clean:
	rm -rf bin obj
