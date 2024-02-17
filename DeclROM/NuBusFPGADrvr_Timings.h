struct vtg_timing_regs {
	unsigned short hres;
	unsigned short hsync_start;
	unsigned short hsync_end;
	unsigned short hscan;
	unsigned short vres;
	unsigned short vsync_start;
	unsigned short vsync_end;
	unsigned short vscan;
};
struct vtg_timing_regs vtg_640x480_60Hz = {
	.hres = 640,
	.hsync_start = 656,
	.hsync_end = 752,
	.hscan = 800,
	.vres = 480,
	.vsync_start = 490,
	.vsync_end = 492,
	.vscan = 525
};
struct vtg_timing_regs vtg_640x480_75Hz = {
	.hres = 640,
	.hsync_start = 656,
	.hsync_end = 720,
	.hscan = 840,
	.vres = 480,
	.vsync_start = 481,
	.vsync_end = 484,
	.vscan = 500
};
struct vtg_timing_regs vtg_800x600_60Hz = {
	.hres = 800,
	.hsync_start = 840,
	.hsync_end = 968,
	.hscan = 1056,
	.vres = 600,
	.vsync_start = 601,
	.vsync_end = 605,
	.vscan = 628
};
struct vtg_timing_regs vtg_800x600_75Hz = {
	.hres = 800,
	.hsync_start = 816,
	.hsync_end = 896,
	.hscan = 1056,
	.vres = 600,
	.vsync_start = 601,
	.vsync_end = 604,
	.vscan = 625
};
struct vtg_timing_regs vtg_1024x768_60Hz = {
	.hres = 1024,
	.hsync_start = 1048,
	.hsync_end = 1184,
	.hscan = 1344,
	.vres = 768,
	.vsync_start = 771,
	.vsync_end = 777,
	.vscan = 806
};
struct vtg_timing_regs vtg_1024x768_75Hz = {
	.hres = 1024,
	.hsync_start = 1040,
	.hsync_end = 1136,
	.hscan = 1312,
	.vres = 768,
	.vsync_start = 769,
	.vsync_end = 772,
	.vscan = 800
};
struct vtg_timing_regs vtg_1280x720_60Hz = {
	.hres = 1280,
	.hsync_start = 1500,
	.hsync_end = 1540,
	.hscan = 1650,
	.vres = 720,
	.vsync_start = 725,
	.vsync_end = 730,
	.vscan = 750
};
struct vtg_timing_regs vtg_1280x1024_60Hz = {
	.hres = 1280,
	.hsync_start = 1328,
	.hsync_end = 1440,
	.hscan = 1688,
	.vres = 1024,
	.vsync_start = 1025,
	.vsync_end = 1028,
	.vscan = 1066
};
struct vtg_timing_regs vtg_1920x1080_30Hz = {
	.hres = 1920,
	.hsync_start = 2448,
	.hsync_end = 2492,
	.hscan = 2640,
	.vres = 1080,
	.vsync_start = 1084,
	.vsync_end = 1089,
	.vscan = 1125
};
struct vtg_timing_regs vtg_1920x1080_60Hz = {
	.hres = 1920,
	.hsync_start = 2008,
	.hsync_end = 2052,
	.hscan = 2200,
	.vres = 1080,
	.vsync_start = 1084,
	.vsync_end = 1089,
	.vscan = 1125
};
