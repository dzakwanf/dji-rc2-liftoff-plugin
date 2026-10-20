#import <Foundation/Foundation.h>
#import <GameController/GameController.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>

#define STATE_FILE_PATH "/tmp/dji_rc2_state.bin"
#ifndef CALIB_FILE_PATH
/* Overridden at compile time by scripts/install.sh via -DCALIB_FILE_PATH=... */
#define CALIB_FILE_PATH "calib.json"
#endif
#define STATE_MAGIC 0x444A4932U /* 'DJI2' */
#define STATE_VERSION 1U

#define DJI_VID 0x2ca3
#define DJI_PID_RC2 0x1021
#define DJI_PID_RC1 0x1023

#pragma pack(push, 1)
typedef struct {
    uint32_t magic;
    uint32_t version;
    double timestamp;
    uint32_t writer_pid;
    uint32_t connected;
    float aileron;     /* Right Stick X [-1.0, 1.0] */
    float elevator;    /* Right Stick Y [-1.0, 1.0] */
    float throttle;    /* Left Stick Y  [-1.0, 1.0] */
    float rudder;      /* Left Stick X  [-1.0, 1.0] */
    float wheel_left;  /* Left Wheel    [-1.0, 1.0] */
    float wheel_right; /* Right Wheel   [-1.0, 1.0] */
    uint16_t raw[6];
    uint16_t cal_min[6];
    uint16_t cal_ctr[6];
    uint16_t cal_max[6];
} DJIRC2SharedState;
#pragma pack(pop)

/* DUML CRC tables (from o-gs/dji-firmware-tools) */
static const uint8_t kCrc8Table[256] = {
    0x00,0x5e,0xbc,0xe2,0x61,0x3f,0xdd,0x83,0xc2,0x9c,0x7e,0x20,0xa3,0xfd,0x1f,0x41,
    0x9d,0xc3,0x21,0x7f,0xfc,0xa2,0x40,0x1e,0x5f,0x01,0xe3,0xbd,0x3e,0x60,0x82,0xdc,
    0x23,0x7d,0x9f,0xc1,0x42,0x1c,0xfe,0xa0,0xe1,0xbf,0x5d,0x03,0x80,0xde,0x3c,0x62,
    0xbe,0xe0,0x02,0x5c,0xdf,0x81,0x63,0x3d,0x7c,0x22,0xc0,0x9e,0x1d,0x43,0xa1,0xff,
    0x46,0x18,0xfa,0xa4,0x27,0x79,0x9b,0xc5,0x84,0xda,0x38,0x66,0xe5,0xbb,0x59,0x07,
    0xdb,0x85,0x67,0x39,0xba,0xe4,0x06,0x58,0x19,0x47,0xa5,0xfb,0x78,0x26,0xc4,0x9a,
    0x65,0x3b,0xd9,0x87,0x04,0x5a,0xb8,0xe6,0xa7,0xf9,0x1b,0x45,0xc6,0x98,0x7a,0x24,
    0xf8,0xa6,0x44,0x1a,0x99,0xc7,0x25,0x7b,0x3a,0x64,0x86,0xd8,0x5b,0x05,0xe7,0xb9,
    0x8c,0xd2,0x30,0x6e,0xed,0xb3,0x51,0x0f,0x4e,0x10,0xf2,0xac,0x2f,0x71,0x93,0xcd,
    0x11,0x4f,0xad,0xf3,0x70,0x2e,0xcc,0x92,0xd3,0x8d,0x6f,0x31,0xb2,0xec,0x0e,0x50,
    0xaf,0xf1,0x13,0x4d,0xce,0x90,0x72,0x2c,0x6d,0x33,0xd1,0x8f,0x0c,0x52,0xb0,0xee,
    0x32,0x6c,0x8e,0xd0,0x53,0x0d,0xef,0xb1,0xf0,0xae,0x4c,0x12,0x91,0xcf,0x2d,0x73,
    0xca,0x94,0x76,0x28,0xab,0xf5,0x17,0x49,0x08,0x56,0xb4,0xea,0x69,0x37,0xd5,0x8b,
    0x57,0x09,0xeb,0xb5,0x36,0x68,0x8a,0xd4,0x95,0xcb,0x29,0x77,0xf4,0xaa,0x48,0x16,
    0xe9,0xb7,0x55,0x0b,0x88,0xd6,0x34,0x6a,0x2b,0x75,0x97,0xc9,0x4a,0x14,0xf6,0xa8,
    0x74,0x2a,0xc8,0x96,0x15,0x4b,0xa9,0xf7,0xb6,0xe8,0x0a,0x54,0xd7,0x89,0x6b,0x35
};

static const uint16_t kCrc16Table[256] = {
    0x0000,0x1189,0x2312,0x329b,0x4624,0x57ad,0x6536,0x74bf,
    0x8c48,0x9dc1,0xaf5a,0xbed3,0xca6c,0xdbe5,0xe97e,0xf8f7,
    0x1081,0x0108,0x3393,0x221a,0x56a5,0x472c,0x75b7,0x643e,
    0x9cc9,0x8d40,0xbfdb,0xae52,0xdaed,0xcb64,0xf9ff,0xe876,
    0x2102,0x308b,0x0210,0x1399,0x6726,0x76af,0x4434,0x55bd,
    0xad4a,0xbcc3,0x8e58,0x9fd1,0xeb6e,0xfae7,0xc87c,0xd9f5,
    0x3183,0x200a,0x1291,0x0318,0x77a7,0x662e,0x54b5,0x453c,
    0xbdcb,0xac42,0x9ed9,0x8f50,0xfbef,0xea66,0xd8fd,0xc974,
    0x4204,0x538d,0x6116,0x709f,0x0420,0x15a9,0x2732,0x36bb,
    0xce4c,0xdfc5,0xed5e,0xfcd7,0x8868,0x99e1,0xab7a,0xbaf3,
    0x5285,0x430c,0x7197,0x601e,0x14a1,0x0528,0x37b3,0x263a,
    0xdecd,0xcf44,0xfddf,0xec56,0x98e9,0x8960,0xbbfb,0xaa72,
    0x6306,0x728f,0x4014,0x519d,0x2522,0x34ab,0x0630,0x17b9,
    0xef4e,0xfec7,0xcc5c,0xddd5,0xa96a,0xb8e3,0x8a78,0x9bf1,
    0x7387,0x620e,0x5095,0x411c,0x35a3,0x242a,0x16b1,0x0738,
    0xffcf,0xee46,0xdcdd,0xcd54,0xb9eb,0xa862,0x9af9,0x8b70,
    0x8408,0x9581,0xa71a,0xb693,0xc22c,0xd3a5,0xe13e,0xf0b7,
    0x0840,0x19c9,0x2b52,0x3adb,0x4e64,0x5fed,0x6d76,0x7cff,
    0x9489,0x8500,0xb79b,0xa612,0xd2ad,0xc324,0xf1bf,0xe036,
    0x18c1,0x0948,0x3bd3,0x2a5a,0x5ee5,0x4f6c,0x7df7,0x6c7e,
    0xa50a,0xb483,0x8618,0x9791,0xe32e,0xf2a7,0xc03c,0xd1b5,
    0x2942,0x38cb,0x0a50,0x1bd9,0x6f66,0x7eef,0x4c74,0x5dfd,
    0xb58b,0xa402,0x9699,0x8710,0xf3af,0xe226,0xd0bd,0xc134,
    0x39c3,0x284a,0x1ad1,0x0b58,0x7fe7,0x6e6e,0x5cf5,0x4d7c,
    0xc60c,0xd785,0xe51e,0xf497,0x8028,0x91a1,0xa33a,0xb2b3,
    0x4a44,0x5bcd,0x6956,0x78df,0x0c60,0x1de9,0x2f72,0x3efb,
    0xd68d,0xc704,0xf59f,0xe416,0x90a9,0x8120,0xb3bb,0xa232,
    0x5ac5,0x4b4c,0x79d7,0x685e,0x1ce1,0x0d68,0x3ff3,0x2e7a,
    0xe70e,0xf687,0xc41c,0xd595,0xa12a,0xb0a3,0x8238,0x93b1,
    0x6b46,0x7acf,0x4854,0x59dd,0x2d62,0x3ceb,0x0e70,0x1ff9,
    0xf78f,0xe606,0xd49d,0xc514,0xb1ab,0xa022,0x92b9,0x8330,
    0x7bc7,0x6a4e,0x58d5,0x495c,0x3de3,0x2c6a,0x1ef1,0x0f78
};

static uint8_t duml_crc8(const uint8_t *data, size_t len) {
    uint8_t crc = 0x77;
    for (size_t i = 0; i < len; i++) crc = kCrc8Table[crc ^ data[i]];
    return crc;
}

static uint16_t duml_crc16(const uint8_t *data, size_t len) {
    uint16_t crc = 0x3692;
    for (size_t i = 0; i < len; i++) crc = (crc >> 8) ^ kCrc16Table[(crc ^ data[i]) & 0xFF];
    return crc;
}

static void build_duml_req(uint8_t out[13], uint8_t sender, uint8_t receiver, uint16_t seq, uint8_t cmd_type, uint8_t cmd_set, uint8_t cmd_id) {
    uint16_t tag = (1U << 10) | 13U;
    out[0] = 0x55;
    out[1] = (uint8_t)(tag & 0xFF);
    out[2] = (uint8_t)((tag >> 8) & 0xFF);
    out[3] = duml_crc8(out, 3);
    out[4] = sender;
    out[5] = receiver;
    out[6] = (uint8_t)(seq & 0xFF);
    out[7] = (uint8_t)((seq >> 8) & 0xFF);
    out[8] = cmd_type;
    out[9] = cmd_set;
    out[10] = cmd_id;
    uint16_t c16 = duml_crc16(out, 11);
    out[11] = (uint8_t)(c16 & 0xFF);
    out[12] = (uint8_t)((c16 >> 8) & 0xFF);
}

static double now_sec(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (double)tv.tv_sec + (double)tv.tv_usec * 1e-6;
}

/* Bipolar scaling for self-centering sticks (roll, pitch, yaw).
   Center maps to 0.0, with a deadzone around it.

   "hi" is the end the channel counts towards as the stick goes one way and
   "lo" is the other. A channel that reports backwards arrives with the two
   swapped, which flips the sign of the result below, so the direction comes
   from the calibration instead of being guessed. */
static float scale_axis(uint16_t raw, uint16_t lo, uint16_t ctr, uint16_t hi, float deadzone) {
    float frac = 0.0f;
    if (raw >= ctr) {
        int span = (int)hi - (int)ctr;
        if (span != 0) frac = (float)((int)raw - (int)ctr) / (float)span;
    } else {
        int span = (int)ctr - (int)lo;
        if (span != 0) frac = (float)((int)raw - (int)ctr) / (float)span;
    }
    float a = fabsf(frac);
    if (a <= deadzone) return 0.0f;
    float sign = (frac >= 0.0f) ? 1.0f : -1.0f;
    float scaled = sign * ((a - deadzone) / (1.0f - deadzone));
    if (scaled > 1.0f) scaled = 1.0f;
    if (scaled < -1.0f) scaled = -1.0f;
    return scaled;
}

/* Lever scaling for a throttle that rests at one end, which is what the DJI
   RC 2's left stick does: it springs back, and the resting position is the
   low end of the range.

   The output spans -1 .. +1 with the resting position at -1 and the stick
   pushed up at +1. The whole travel from resting to fully up is used, so the
   throttle still has the full resolution of the stick, and the axis can
   actually reach its low end. That last part matters for arming: Liftoff arms
   on throttle low plus yaw, and a lever that only ever reports 0 .. 1 sits in
   the middle of the axis, where the arm gesture can never be satisfied.

   The calibration carries the direction: "hi" is wherever the channel counts
   towards as the stick goes up. If the controller reports that channel
   backwards, the recorded min and max simply arrive swapped, so "hi" ends up
   smaller than "ctr" and the division below still produces the right sign.
   That is why the ends are swapped in the config instead of the result being
   negated afterwards: negating a value already clamped at the low end would
   make the whole lower half of the stick read as full throttle. */
static float scale_axis_lever(uint16_t raw, uint16_t lo, uint16_t ctr, uint16_t hi) {
    (void)lo;
    int span = (int)hi - (int)ctr;
    if (span == 0) return -1.0f;
    float frac = (float)((int)raw - (int)ctr) / (float)span;
    if (frac > 1.0f) frac = 1.0f;
    if (frac < 0.0f) frac = 0.0f;
    /* Map the 0 .. 1 travel onto -1 .. +1, resting at the low end. */
    return frac * 2.0f - 1.0f;
}
/* libusb dynamic function pointers */
typedef struct libusb_context libusb_context;
typedef struct libusb_device_handle libusb_device_handle;
typedef int (*libusb_init_fn)(libusb_context **);
typedef void (*libusb_exit_fn)(libusb_context *);
typedef libusb_device_handle *(*libusb_open_device_with_vid_pid_fn)(libusb_context *, uint16_t, uint16_t);
typedef void (*libusb_close_fn)(libusb_device_handle *);
typedef int (*libusb_set_auto_detach_kernel_driver_fn)(libusb_device_handle *, int);
typedef int (*libusb_claim_interface_fn)(libusb_device_handle *, int);
typedef int (*libusb_release_interface_fn)(libusb_device_handle *, int);
typedef int (*libusb_bulk_transfer_fn)(libusb_device_handle *, unsigned char, unsigned char *, int, int *, unsigned int);

/* Rewired_MacOS_orig.bundle function pointers */
typedef void (*RWCallback)(void *);
typedef bool (*RWInitFn)(RWCallback, RWCallback);
typedef bool (*RWDisposeFn)(void);
typedef void (*RWUpdateFn)(void);
typedef void (*RWOnConnectedFn)(GCController *);

static void *g_origBundle = NULL;
static RWInitFn g_origInit = NULL;
static RWDisposeFn g_origDispose = NULL;
static RWUpdateFn g_origUpdate = NULL;
static RWOnConnectedFn g_origOnConnected = NULL;

static GCController *g_virtualCtrl = nil;
static dispatch_queue_t g_ctrlQueue = nil;
static DJIRC2SharedState *g_shm = NULL;
static DJIRC2SharedState g_localState;

/* Channels whose calibration came from calib.json. The controller also reports
   its own calibration table, and those readings would otherwise overwrite the
   file on every connection. Marking the JSON-sourced channels keeps the file
   authoritative, which matters because it is the one the user edits: if the
   controller silently replaced it, tuned values would look like they did
   nothing. Kept separate from the shared struct so the memory layout that the
   Python bridge unpacks stays unchanged. */
static int g_calibFromJson[6] = {0, 0, 0, 0, 0, 0};
static pthread_mutex_t g_stateMutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_t g_usbThread;
static volatile int g_running = 0;

/* ---------------------------------------------------------------------------
 * Axis mapping configuration
 *
 * DJI reports six raw channels in a fixed order. Which physical stick each one
 * corresponds to, and which way it points, varies between units and between
 * firmware versions. Rather than hardcoding it, we describe the mapping here
 * and let the user override any entry from calib.json ("mapping" section).
 *
 * The defaults below are the DJI RC 2 (rc331) layout in Mode 2:
 *   raw[0] = right stick horizontal  -> roll   (aileron)
 *   raw[1] = right stick vertical    -> pitch  (elevator), inverted
 *   raw[2] = left  stick vertical    -> throttle
 *   raw[3] = left  stick horizontal  -> yaw    (rudder)
 *   raw[4] = left  top wheel         -> aux
 *   raw[5] = right top wheel         -> aux
 * ------------------------------------------------------------------------- */

typedef enum {
    AXIS_ROLL = 0,
    AXIS_PITCH,
    AXIS_THROTTLE,
    AXIS_YAW,
    AXIS_AUX_L,
    AXIS_AUX_R,
    AXIS_COUNT
} AxisRole;

typedef struct {
    int source;   /* index into the raw[6] array reported by the controller */
    int invert;   /* 1 = flip the sign of the scaled value */
    int center;   /* 1 = rests in the middle (bipolar), 0 = rests at one end (lever) */
} AxisMapEntry;

static AxisMapEntry g_axisMap[AXIS_COUNT] = {
    { 0, 0, 1 },  /* ROLL      <- raw[0], bipolar          */
    { 1, 0, 1 },  /* PITCH     <- raw[1], bipolar          */
    { 2, 0, 1 },  /* THROTTLE  <- raw[2], bipolar          */
    { 3, 0, 1 },  /* YAW       <- raw[3], bipolar          */
    { 4, 0, 1 },  /* AUX_L     <- raw[4]                   */
    { 5, 0, 1 },  /* AUX_R     <- raw[5]                   */
};

static const char *const kAxisRoleNames[AXIS_COUNT] = {
    "roll", "pitch", "throttle", "yaw", "aux_left", "aux_right"
};


/* A calibration range this narrow means the channel was never actually moved
   during calibration, so the recorded values are pure noise. Feeding such a
   range into scale_axis() turns 1-2 LSB of ADC jitter into full-scale swings,
   which is what makes a channel look like an unstable signal. */
#define MIN_USABLE_SPAN 200

static void plugin_log(const char *fmt, ...);

static void init_shared_state_defaults(DJIRC2SharedState *st) {
    memset(st, 0, sizeof(*st));
    st->magic = STATE_MAGIC;
    st->version = STATE_VERSION;
    /* Default DJI RC 2 calibration values from hardware 0x06/0x38 */
    const uint16_t def_min[6] = {479, 507, 533, 481, 494, 504};
    const uint16_t def_ctr[6] = {1642, 1707, 1701, 1612, 1732, 1745};
    const uint16_t def_max[6] = {2864, 2874, 2826, 2789, 2732, 2755};
    for (int i = 0; i < 6; i++) {
        st->cal_min[i] = def_min[i];
        st->cal_ctr[i] = def_ctr[i];
        st->cal_max[i] = def_max[i];
        st->raw[i] = def_ctr[i];
    }
}

static void load_axis_mapping_if_present(NSDictionary *json) {
    NSDictionary *mapping = json[@"mapping"];
    if (![mapping isKindOfClass:[NSDictionary class]]) return;
    for (int role = 0; role < AXIS_COUNT; role++) {
        NSString *key = [NSString stringWithUTF8String:kAxisRoleNames[role]];
        NSDictionary *entry = mapping[key];
        if (![entry isKindOfClass:[NSDictionary class]]) continue;
        if (entry[@"source"]) {
            int src = [entry[@"source"] intValue];
            if (src >= 0 && src < 6) g_axisMap[role].source = src;
        }
        if (entry[@"invert"])   g_axisMap[role].invert = [entry[@"invert"] boolValue] ? 1 : 0;
        if (entry[@"center"])   g_axisMap[role].center = [entry[@"center"] boolValue] ? 1 : 0;
    }
}

static void load_calib_json_if_present(DJIRC2SharedState *st) {
    NSData *data = [NSData dataWithContentsOfFile:@CALIB_FILE_PATH];
    if (!data) return;
    NSDictionary *json = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    if (![json isKindOfClass:[NSDictionary class]]) return;
    load_axis_mapping_if_present(json);
    NSDictionary *axes = json[@"axes"];
    if (![axes isKindOfClass:[NSDictionary class]]) return;
    NSArray<NSString *> *names = @[@"aileron", @"elevator", @"throttle", @"rudder", @"wheel_left", @"wheel_right"];
    for (int i = 0; i < 6; i++) {
        NSDictionary *a = axes[names[i]];
        if ([a isKindOfClass:[NSDictionary class]]) {
            uint16_t mn = a[@"min"]    ? (uint16_t)[a[@"min"] unsignedIntValue]    : st->cal_min[i];
            uint16_t ct = a[@"center"] ? (uint16_t)[a[@"center"] unsignedIntValue] : st->cal_ctr[i];
            uint16_t mx = a[@"max"]    ? (uint16_t)[a[@"max"] unsignedIntValue]    : st->cal_max[i];
            /* Skip ranges that are too narrow to be real, or self-inconsistent.
               Either direction is fine: a backwards channel reports min and max
               swapped, and the unipolar/bipolar scalers read the direction from
               those values rather than assuming min is always the low end. */
            int lo_end = (mn < mx) ? mn : mx;
            int hi_end = (mn < mx) ? mx : mn;
            BOOL sane = (lo_end < ct && ct < hi_end) &&
                        ((hi_end - lo_end) >= MIN_USABLE_SPAN);
            if (sane) {
                st->cal_min[i] = mn;
                st->cal_ctr[i] = ct;
                st->cal_max[i] = mx;
                g_calibFromJson[i] = 1;
            } else {
                plugin_log("calib: channel %d ignored (span=%d, min=%u ctr=%u max=%u) - keeping default\n",
                           i, (int)(mx - mn), mn, ct, mx);
            }
        }
    }
}

static void setup_shm(void) {
    int fd = open(STATE_FILE_PATH, O_RDWR | O_CREAT, 0666);
    if (fd < 0) return;
    fchmod(fd, 0666);
    struct stat sb;
    if (fstat(fd, &sb) == 0 && sb.st_size < (off_t)sizeof(DJIRC2SharedState)) {
        DJIRC2SharedState tmp;
        init_shared_state_defaults(&tmp);
        load_calib_json_if_present(&tmp);
        write(fd, &tmp, sizeof(tmp));
    }
    void *map = mmap(NULL, sizeof(DJIRC2SharedState), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (map != MAP_FAILED) {
        g_shm = (DJIRC2SharedState *)map;
        if (g_shm->magic != STATE_MAGIC) {
            init_shared_state_defaults(g_shm);
            load_calib_json_if_present(g_shm);
        }
    }
}

static void parse_duml_buffer(uint8_t *buf, int len, DJIRC2SharedState *st, bool *got_f5) {
    int i = 0;
    while (i + 13 <= len) {
        if (buf[i] != 0x55) { i++; continue; }
        int plen = buf[i + 1] | ((buf[i + 2] & 0x03) << 8);
        if (plen < 13 || plen > 512 || duml_crc8(&buf[i], 3) != buf[i + 3]) {
            i++;
            continue;
        }
        if (i + plen > len) break;
        uint16_t expected_crc = (uint16_t)buf[i + plen - 2] | ((uint16_t)buf[i + plen - 1] << 8);
        if (duml_crc16(&buf[i], plen - 2) == expected_crc) {
            uint8_t cmd_set = buf[i + 9];
            uint8_t cmd_id = buf[i + 10];
            const uint8_t *pay = &buf[i + 11];
            int pay_len = plen - 13;
            if (cmd_set == 0x06 && cmd_id == 0x38 && pay_len >= 37) {
                /* Hardware stick calibration table: 6 * (min, center, max).
                   A channel that counts backwards reports its ends swapped, so
                   the range is accepted in either direction. What matters is
                   that the center sits between the two ends and the range is
                   wide enough to be a real axis rather than sensor noise. */
                for (int c = 0; c < 6; c++) {
                    const uint8_t *p = pay + 1 + c * 6;
                    uint16_t mn = (uint16_t)p[0] | ((uint16_t)p[1] << 8);
                    uint16_t ct = (uint16_t)p[2] | ((uint16_t)p[3] << 8);
                    uint16_t mx = (uint16_t)p[4] | ((uint16_t)p[5] << 8);
                    /* A channel calibrated from the file keeps the file's
                       values: the controller repeats this table periodically
                       and would otherwise undo the user's calibration. */
                    if (g_calibFromJson[c]) continue;
                    int lo_end = (mn < mx) ? mn : mx;
                    int hi_end = (mn < mx) ? mx : mn;
                    int usable = (lo_end < ct && ct < hi_end &&
                                  (hi_end - lo_end) >= MIN_USABLE_SPAN);
                    if (usable) {
                        st->cal_min[c] = mn;
                        st->cal_ctr[c] = ct;
                        st->cal_max[c] = mx;
                    }
                }
            } else if (cmd_set == 0x06 && cmd_id == 0xf5 && pay_len >= 13) {
                for (int c = 0; c < 6; c++) {
                    st->raw[c] = (uint16_t)pay[1 + c * 2] | ((uint16_t)pay[2 + c * 2] << 8);
                }
                /* Scale each physical axis through its configured mapping,
                   then route it to the role it was assigned.
                   Self-centering sticks are scaled bipolar around their centre,
                   levers such as the throttle are scaled from their resting
                   position so the axis still reaches its low end. */
                float scaled[6];
                for (int c = 0; c < 6; c++) {
                    /* Find out whether any role using this channel is a lever. */
                    int lever = 0;
                    for (int role = 0; role < AXIS_COUNT; role++) {
                        if (g_axisMap[role].source == c && !g_axisMap[role].center) {
                            lever = 1;
                            break;
                        }
                    }
                    if (lever) {
                        scaled[c] = scale_axis_lever(st->raw[c], st->cal_min[c], st->cal_ctr[c], st->cal_max[c]);
                    } else {
                        float deadzone = (c >= 4) ? 0.02f : 0.005f;
                        scaled[c] = scale_axis(st->raw[c], st->cal_min[c], st->cal_ctr[c], st->cal_max[c], deadzone);
                    }
                }
                float role_value[AXIS_COUNT];
                for (int role = 0; role < AXIS_COUNT; role++) {
                    int src = g_axisMap[role].source;
                    float v = (src >= 0 && src < 6) ? scaled[src] : 0.0f;
                    if (g_axisMap[role].invert) {
                        /* Directions are normally fixed by the calibration ends,
                           so this is a deliberate override for a role that still
                           feels wrong. Every axis is signed now, so inverting
                           simply flips the sign. */
                        v = -v;
                    }
                    role_value[role] = v;
                }
                st->aileron     = role_value[AXIS_ROLL];
                st->elevator    = role_value[AXIS_PITCH];
                st->throttle    = role_value[AXIS_THROTTLE];
                st->rudder      = role_value[AXIS_YAW];
                st->wheel_left  = role_value[AXIS_AUX_L];
                st->wheel_right = role_value[AXIS_AUX_R];
                st->timestamp   = now_sec();
                st->writer_pid  = (uint32_t)getpid();
                st->connected   = 1;
                if (got_f5) *got_f5 = true;
            }
        }
        i += plen;
    }
}

static void *usb_poll_thread(void *arg) {
    (void)arg;
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);

    void *usb_lib = dlopen("/opt/homebrew/lib/libusb-1.0.dylib", RTLD_LAZY | RTLD_LOCAL);
    if (!usb_lib) usb_lib = dlopen("/usr/local/lib/libusb-1.0.dylib", RTLD_LAZY | RTLD_LOCAL);
    if (!usb_lib) usb_lib = dlopen("libusb-1.0.dylib", RTLD_LAZY | RTLD_LOCAL);

    libusb_init_fn fn_init = usb_lib ? (libusb_init_fn)dlsym(usb_lib, "libusb_init") : NULL;
    libusb_exit_fn fn_exit = usb_lib ? (libusb_exit_fn)dlsym(usb_lib, "libusb_exit") : NULL;
    libusb_open_device_with_vid_pid_fn fn_open = usb_lib ? (libusb_open_device_with_vid_pid_fn)dlsym(usb_lib, "libusb_open_device_with_vid_pid") : NULL;
    libusb_close_fn fn_close = usb_lib ? (libusb_close_fn)dlsym(usb_lib, "libusb_close") : NULL;
    libusb_set_auto_detach_kernel_driver_fn fn_detach = usb_lib ? (libusb_set_auto_detach_kernel_driver_fn)dlsym(usb_lib, "libusb_set_auto_detach_kernel_driver") : NULL;
    libusb_claim_interface_fn fn_claim = usb_lib ? (libusb_claim_interface_fn)dlsym(usb_lib, "libusb_claim_interface") : NULL;
    libusb_release_interface_fn fn_release = usb_lib ? (libusb_release_interface_fn)dlsym(usb_lib, "libusb_release_interface") : NULL;
    libusb_bulk_transfer_fn fn_bulk = usb_lib ? (libusb_bulk_transfer_fn)dlsym(usb_lib, "libusb_bulk_transfer") : NULL;

    libusb_context *ctx = NULL;
    if (fn_init) fn_init(&ctx);

    libusb_device_handle *dev = NULL;
    int iface = 0;
    unsigned char ep_out = 0x01;
    unsigned char ep_in = 0x81;
    uint16_t seq = 1;
    uint32_t my_pid = (uint32_t)getpid();

    while (g_running) {
        /* If an external Python bridge is actively updating /tmp/dji_rc2_state.bin, yield USB to it */
        if (g_shm && g_shm->magic == STATE_MAGIC && g_shm->writer_pid != 0 &&
            g_shm->writer_pid != my_pid && (now_sec() - g_shm->timestamp) < 0.30) {
            if (dev) {
                fn_release(dev, iface);
                fn_close(dev);
                dev = NULL;
            }
            pthread_mutex_lock(&g_stateMutex);
            g_localState = *g_shm;
            pthread_mutex_unlock(&g_stateMutex);
            usleep(2000);
            continue;
        }

        if (!dev && fn_open) {
            dev = fn_open(ctx, DJI_VID, DJI_PID_RC2);
            if (dev) {
                iface = 0; ep_out = 0x01; ep_in = 0x81;
            } else {
                dev = fn_open(ctx, DJI_VID, DJI_PID_RC1);
                if (dev) {
                    iface = 1; ep_out = 0x02; ep_in = 0x83;
                }
            }
            if (dev) {
                if (fn_detach) fn_detach(dev, 1);
                if (fn_claim(dev, iface) != 0) {
                    fn_close(dev);
                    dev = NULL;
                } else {
                    /* Drain & query hardware calibration (0x06/0x38) */
                    uint8_t rbuf[512];
                    int xfer = 0;
                    while (fn_bulk(dev, ep_in, rbuf, sizeof(rbuf), &xfer, 5) == 0 && xfer > 0) {}
                    uint8_t pkt38[13];
                    build_duml_req(pkt38, 10, 6, ++seq, 0x40, 0x06, 0x38);
                    fn_bulk(dev, ep_out, pkt38, 13, &xfer, 25);
                    pthread_mutex_lock(&g_stateMutex);
                    for (int tries = 0; tries < 5; tries++) {
                        if (fn_bulk(dev, ep_in, rbuf, sizeof(rbuf), &xfer, 15) == 0 && xfer > 0) {
                            parse_duml_buffer(rbuf, xfer, &g_localState, NULL);
                        } else {
                            break;
                        }
                    }
                    /* Read the config last so it wins over the hardware table.
                       Order matters: calib.json is the file the user edits, so
                       having the controller silently overwrite it would make
                       every hand-tuned value look like it had no effect. The
                       hardware values still seed the defaults, which is what
                       makes a fresh install work before any calibration. */
                    load_calib_json_if_present(&g_localState);
                    pthread_mutex_unlock(&g_stateMutex);
                }
            }
        }

        if (!dev) {
            usleep(100000); /* Retry USB every 100ms */
            continue;
        }

        uint8_t pkt[13];
        build_duml_req(pkt, 10, 6, ++seq, 0x40, 0x06, 0xf5);
        int xfer = 0;
        int rc = fn_bulk(dev, ep_out, pkt, 13, &xfer, 15);
        if (rc < 0) {
            fn_release(dev, iface);
            fn_close(dev);
            dev = NULL;
            if (g_shm) g_shm->connected = 0;
            usleep(50000);
            continue;
        }

        uint8_t rbuf[512];
        bool any_f5 = false;
        /* Read response and drain any queued packets so there is zero buffer lag */
        for (int reads = 0; reads < 8; reads++) {
            unsigned int timeout_ms = (reads == 0) ? 6 : 1;
            rc = fn_bulk(dev, ep_in, rbuf, sizeof(rbuf), &xfer, timeout_ms);
            if (rc == 0 && xfer > 0) {
                bool got_f5 = false;
                pthread_mutex_lock(&g_stateMutex);
                parse_duml_buffer(rbuf, xfer, &g_localState, &got_f5);
                if (got_f5) any_f5 = true;
                pthread_mutex_unlock(&g_stateMutex);
            } else {
                break;
            }
        }
        if (any_f5 && g_shm) {
            pthread_mutex_lock(&g_stateMutex);
            *g_shm = g_localState;
            pthread_mutex_unlock(&g_stateMutex);
        }
        usleep(1000); /* High-speed low-latency poll */
    }

    if (dev) {
        fn_release(dev, iface);
        fn_close(dev);
    }
    if (ctx && fn_exit) fn_exit(ctx);
    return NULL;
}

static void ensure_orig_loaded(void) {
    if (g_origBundle) return;
    Dl_info info;
    if (dladdr((const void *)&ensure_orig_loaded, &info) && info.dli_fname) {
        NSString *selfPath = [NSString stringWithUTF8String:info.dli_fname];
        NSString *dir = [selfPath stringByDeletingLastPathComponent];
        NSString *origPath = [dir stringByAppendingPathComponent:@"Rewired_MacOS_orig.bundle"];
        g_origBundle = dlopen([origPath UTF8String], RTLD_NOW | RTLD_LOCAL);
    }
    if (!g_origBundle) {
        /* Fallback: honor LIFTOFF_APP if set, otherwise the default Steam location. */
        const char *appEnv = getenv("LIFTOFF_APP");
        NSString *appPath = appEnv && *appEnv
            ? [NSString stringWithUTF8String:appEnv]
            : [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/Steam/steamapps/common/Liftoff/Liftoff.app"];
        NSString *origPath = [appPath stringByAppendingPathComponent:@"Contents/PlugIns/Rewired_MacOS_orig.bundle"];
        g_origBundle = dlopen([origPath UTF8String], RTLD_NOW | RTLD_LOCAL);
    }
    if (g_origBundle) {
        g_origInit = (RWInitFn)dlsym(g_origBundle, "Initialize");
        g_origDispose = (RWDisposeFn)dlsym(g_origBundle, "Dispose");
        g_origUpdate = (RWUpdateFn)dlsym(g_origBundle, "Update");
        g_origOnConnected = (RWOnConnectedFn)dlsym(g_origBundle, "_ZN12RWController23T_OnControllerConnectedEP12GCController");
    }
}

static void plugin_log(const char *fmt, ...) {
    FILE *fp = fopen("/tmp/dji_rc2_plugin.log", "a");
    if (!fp) return;
    va_list ap;
    va_start(ap, fmt);
    fprintf(fp, "[%.3f pid=%d] ", now_sec(), (int)getpid());
    vfprintf(fp, fmt, ap);
    fprintf(fp, "\n");
    va_end(ap);
    fclose(fp);
}

__attribute__((visibility("default")))
bool Initialize(RWCallback onControllerConnected, RWCallback onControllerDisconnected) {
    @autoreleasepool {
        ensure_orig_loaded();
        init_shared_state_defaults(&g_localState);
        load_calib_json_if_present(&g_localState);
        setup_shm();

        bool res = g_origInit ? g_origInit(onControllerConnected, onControllerDisconnected) : false;

        if (!g_virtualCtrl) {
            g_virtualCtrl = [[GCController controllerWithExtendedGamepad] retain];
            @try {
                [g_virtualCtrl setValue:@"DJI RC 2 Controller" forKey:@"vendorName"];
            } @catch (NSException *ex) {}
            g_ctrlQueue = dispatch_queue_create("com.dji.rc2.liftoff", DISPATCH_QUEUE_SERIAL);
            g_virtualCtrl.handlerQueue = g_ctrlQueue;
        }
        if (g_origOnConnected && g_virtualCtrl) {
            g_origOnConnected(g_virtualCtrl);
        }

        if (!g_running) {
            g_running = 1;
            pthread_create(&g_usbThread, NULL, usb_poll_thread, NULL);
        }
        plugin_log("Initialize called: res=%d virtualCtrl=%p origOnConnected=%p", (int)res, g_virtualCtrl, g_origOnConnected);
        return res;
    }
}

__attribute__((visibility("default")))
void Update(void) {
    @autoreleasepool {
        ensure_orig_loaded();
        if (g_virtualCtrl && g_ctrlQueue) {
            DJIRC2SharedState st;
            pthread_mutex_lock(&g_stateMutex);
            if (g_shm && g_shm->magic == STATE_MAGIC && (now_sec() - g_shm->timestamp) < 0.50) {
                st = *g_shm;
            } else {
                st = g_localState;
            }
            pthread_mutex_unlock(&g_stateMutex);

            GCExtendedGamepad *gp = g_virtualCtrl.extendedGamepad;
            if (gp) {
                /* Values are already normalized and sign-corrected by g_axisMap,
                   so they are fed through verbatim here. */
                [gp.leftThumbstick.xAxis setValue:st.rudder];
                [gp.leftThumbstick.yAxis setValue:st.throttle];
                [gp.rightThumbstick.xAxis setValue:st.aileron];
                [gp.rightThumbstick.yAxis setValue:st.elevator];

                /* Map top wheels to triggers (when rolled right) and shoulder buttons (when rolled left)
                   so all triggers & buttons rest cleanly at 0.0 when untouched */
                float l_trig = (st.wheel_left > 0.05f) ? st.wheel_left : 0.0f;
                float r_trig = (st.wheel_right > 0.05f) ? st.wheel_right : 0.0f;
                float l_shld = (st.wheel_left < -0.55f) ? 1.0f : 0.0f;
                float r_shld = (st.wheel_right < -0.55f) ? 1.0f : 0.0f;

                [gp.leftTrigger setValue:l_trig];
                [gp.rightTrigger setValue:r_trig];
                [gp.leftShoulder setValue:l_shld];
                [gp.rightShoulder setValue:r_shld];

                dispatch_sync(g_ctrlQueue, ^{});
            }
        }
        if (g_origUpdate) g_origUpdate();
    }
}

__attribute__((visibility("default")))
bool Dispose(void) {
    @autoreleasepool {
        if (g_running) {
            g_running = 0;
            pthread_join(g_usbThread, NULL);
        }
        ensure_orig_loaded();
        return g_origDispose ? g_origDispose() : false;
    }
}
