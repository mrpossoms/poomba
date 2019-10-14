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

obj/%.o: %.c 
	$(CC) $(CFLAGS) -c $< -o $@

hwd: obj $(OBJS)
	@echo $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o bin/$@

.PHONY: install
install:
	ln -s $(shell pwd)/bin/hwd /usr/bin/hwd

.PHONY: clean
clean:
	rm -rf bin obj
