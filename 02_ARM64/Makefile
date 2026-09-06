AS = aarch64-linux-gnu-as
LD = aarch64-linux-gnu-ld

TARGET = arm64_stats
OBJECT = arm64_stats.o
SOURCE = arm64_stats.s

all: $(TARGET)

$(TARGET): $(OBJECT)
	$(LD) -o $(TARGET) $(OBJECT)

$(OBJECT): $(SOURCE)
	$(AS) -g -o $(OBJECT) $(SOURCE)

run: $(TARGET)
	qemu-aarch64 ./$(TARGET)

clean:
	rm -f $(OBJECT) $(TARGET) resultado.txt

