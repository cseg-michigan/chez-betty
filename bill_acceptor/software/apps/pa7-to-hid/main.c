
#include <stdio.h>
#include <stdlib.h>

#include "bsp.h"
#include "ioc.h"
#include "gptimer.h"
#include "bsp_led.h"
#include "string.h"
#include "usb_hid.h"
#include "usb_firmware_library_headers.h"


//*****************************************************************************
//
// Local functions
//
//*****************************************************************************
void selKeyRemoteWakeupIsr(void) {
    usbsuspDoRemoteWakeup();
    IntDisable(INT_GPIOA);
}


void dirKeyRemoteWakeupIsr(void) {
    usbsuspDoRemoteWakeup();
    IntDisable(INT_GPIOC);
}


//*****************************************************************************
//
// Implementations of function that are required by usb framework.
//
//*****************************************************************************
void usbsuspHookEnteringSuspend(bool remoteWakeupAllowed) {
    if (remoteWakeupAllowed) {
        GPIOPowIntClear(BSP_KEY_SEL_BASE, BSP_KEY_SELECT);
        GPIOPowIntEnable(BSP_KEY_SEL_BASE, BSP_KEY_SELECT);
        IntPendClear(INT_GPIOA);
        IntEnable(INT_GPIOA);

        GPIOPowIntClear(BSP_KEY_DIR_BASE, BSP_KEY_DIR_ALL);
        GPIOPowIntEnable(BSP_KEY_DIR_BASE, BSP_KEY_DIR_ALL);
        IntPendClear(INT_GPIOC);
        IntEnable(INT_GPIOC);
    }
}


void usbsuspHookExitingSuspend(void) {
    IntDisable(INT_GPIOA);
    GPIOPowIntDisable(BSP_KEY_SEL_BASE, BSP_KEY_SELECT);

    IntDisable(INT_GPIOC);
    GPIOPowIntDisable(BSP_KEY_DIR_BASE, BSP_KEY_DIR_ALL);
}

uint8_t send = 0;
uint8_t count = 0;
uint32_t last_interrupt_time = 0;

void gpio_toggle (uint32_t base, uint8_t ui8Leds) {
    uint32_t ui32Toggle = GPIOPinRead(base, ui8Leds);
    ui32Toggle = (~ui32Toggle) & ui8Leds;
    GPIOPinWrite(base, ui8Leds, ui32Toggle);
}






void GPIOBIntHandler(void) {
    uint32_t ui32GPIOIntStatus;

    bspLedToggle(BSP_LED_1);

    // Get the masked interrupt status.
    ui32GPIOIntStatus = GPIOPinIntStatus(GPIO_B_BASE, true);

    // Acknowledge the GPIO  - Pin n interrupt by clearing the interrupt flag.
    GPIOPinIntClear(GPIO_B_BASE, ui32GPIOIntStatus);

    // Check to make sure this is valid, and to debounce (not strictly sure
    // this is necessary...).
    bool valid_pulse = false;

    if (count == 0) {
        // On first edge we know we are good
        valid_pulse = true;
    } else {
        // See if this is a valid edge
        uint32_t curr_time = TimerValueGet(GPTIMER0_BASE, GPTIMER_A);
        // Must be at least 30 ms from last edge
        if ((last_interrupt_time - curr_time) > (SysCtrlClockGet() / 33)) {
            valid_pulse = true;
        }
    }

    // Increment our dollar count and set a timeout timer
    if (valid_pulse) {

        count += 1;

        // Start a timeout timer
        TimerDisable(GPTIMER0_BASE, GPTIMER_A);
        // Timeout in 100 ms
        TimerLoadSet(GPTIMER0_BASE, GPTIMER_A, SysCtrlClockGet() / 10);
        TimerEnable(GPTIMER0_BASE, GPTIMER_A);

        // Save the time we got this edge so we can detect if the next one
        // is too close.
        last_interrupt_time = TimerValueGet(GPTIMER0_BASE, GPTIMER_A);

        gpio_toggle(GPIO_B_BASE, GPIO_PIN_5);

        // On the first edge send a notice so the listener knows its getting
        // data.
        if (count == 1) {
            send = 2;
        }
    }

}


void Timer0AIntHandler(void) {
    // Clear the timer interrupt flag.
    TimerIntClear(GPTIMER0_BASE, GPTIMER_TIMA_TIMEOUT);

    // Set a flag to indicate that the timeout interrupt occurred
    // and that we should report the dollar amount.
   send = 1;
}




void send_char (char c, bool shift) {
    KEYBOARD_IN_REPORT keybReport;
    memset(&keybReport, 0x00, sizeof(KEYBOARD_IN_REPORT));

    if (shift) {
       keybReport.modifiers    = 2;
       keybReport.pKeyCodes[1] = 0xE1;
    }

    if (c >= 97 && c <= 122) {
        keybReport.pKeyCodes[0] = c - 93;
    } else if (c >= 49 && c <= 57) {
        keybReport.pKeyCodes[0] = c - 19;
    } else if (c == '0') {
        keybReport.pKeyCodes[0] = 39;
    } else if (c == '\n') {
        keybReport.pKeyCodes[0] = 0x28;
    } else {
        keybReport.pKeyCodes[0] = 0x38; // "?"
        keybReport.modifiers    = 2;
        keybReport.pKeyCodes[1] = 0xE1;
    }
    hidUpdateKeyboardInReport(&keybReport);

    while (!hidSendKeyboardInReport()) {
        usbHidProcessEvents();
    }

    // Clear button press
    memset(&keybReport, 0x00, sizeof(KEYBOARD_IN_REPORT));
    hidUpdateKeyboardInReport(&keybReport);

    while (!hidSendKeyboardInReport()) {
        usbHidProcessEvents();
    }
}


void dollars_to_characters (int dollars) {
    char buf[10];
    int offset = 0;

    if (dollars < 100) {
        offset++;
        buf[0] = '0';
    }
    if (dollars < 10) {
        offset++;
        buf[1] = '0';
    }

    itoa(dollars, buf+offset, 10);

    int i;
    for (i=0; i<3; i++) {
        send_char(buf[i], false);
    }

}






//
// Application entry point
//
int main (void) {

    //
    // Initialize board and system clock
    //
    bspInit(SYS_CTRL_32MHZ);

    //
    // Enable the USB interface
    //
    usbHidInit();

    // Initialize GPIO pins for LEDs
    GPIOPinTypeGPIOOutput(BSP_LED_BASE, BSP_LED_2 | BSP_LED_3 | BSP_LED_1);
    GPIOPinTypeGPIOOutput(GPIO_B_BASE, GPIO_PIN_5);

    bspLedSet(BSP_LED_2);
    bspLedSet(BSP_LED_3);
    bspLedSet(BSP_LED_1);



    //
    // Configure interrupt with wakeup for all buttons
    //
    // IntRegister(INT_GPIOB, buttonPress);
    // GPIOPowIntTypeSet(GPIO_B_BASE, GPIO_PIN_6, GPIO_POW_RISING_EDGE);
    // IntRegister(INT_GPIOC, dirKeyRemoteWakeupIsr);
    // GPIOPowIntTypeSet(BSP_KEY_DIR_BASE, BSP_KEY_DIR_ALL, GPIO_POW_RISING_EDGE);

    GPIOPinTypeGPIOInput(GPIO_B_BASE, GPIO_PIN_6);
    IOCPadConfigSet(GPIO_B_BASE, GPIO_PIN_6, IOC_OVERRIDE_DIS);
    GPIOIntTypeSet(GPIO_B_BASE, GPIO_PIN_6, GPIO_RISING_EDGE);
    GPIOPinIntEnable(GPIO_B_BASE, GPIO_PIN_6);

    IntMasterEnable();
    IntEnable(INT_GPIOB);




    // setup timer
    SysCtrlPeripheralEnable(SYS_CTRL_PERIPH_GPT0);
    TimerConfigure(GPTIMER0_BASE, GPTIMER_CFG_ONE_SHOT);
    TimerIntEnable(GPTIMER0_BASE, GPTIMER_TIMA_TIMEOUT);
    IntEnable(INT_TIMER0A);






    bspLedClear(BSP_LED_2);

    // Main loop
    while (1) {

        // Process USB events
        usbHidProcessEvents();

        if (send == 1) {
            send = 0;

            uint8_t local_count = count;
            count = 0;

            bspLedToggle(BSP_LED_3);

            send_char('b', true);
            send_char('i', true);
            send_char('l', true);
            send_char('l', true);

            dollars_to_characters(local_count);

            // // if (local_count > 0 && local_count < 3) {
            // if (local_count == 1) {
            //     send_char('0', false);
            //     send_char('0', false);
            //     send_char('1', false);
            // // } else if (local_count >= 3 && local_count < 7) {
            // } else if (local_count == 5) {
            //     send_char('0', false);
            //     send_char('0', false);
            //     send_char('5', false);
            // // } else if (local_count >= 8 && local_count < 12) {
            // } else if (local_count == 10) {
            //     send_char('0', false);
            //     send_char('1', false);
            //     send_char('0', false);
            // // } else if (local_count >= 17 && local_count < 22) {
            // } else if (local_count == 20) {
            //     send_char('0', false);
            //     send_char('2', false);
            //     send_char('0', false);
            // // } else if (local_count >= 45 && local_count < 55) {
            // } else if (local_count == 50) {
            //     send_char('0', false);
            //     send_char('5', false);
            //     send_char('0', false);
            // // } else if (local_count >= 90 && local_count < 110) {
            // } else if (local_count == 100) {
            //     send_char('1', false);
            //     send_char('0', false);
            //     send_char('0', false);
            // } else {
            //     send_char('e', true);
            //     send_char('r', true);
            //     send_char('r', true);
            // }

            // // send_char('\n', false);




        } else if (send == 2) {
            send = 0;

            send_char('b', true);
            send_char('i', true);
            send_char('l', true);
            send_char('l', true);
            send_char('b', true);
            send_char('e', true);
            send_char('g', true);

            // send_char('\n', false);
        }

    }

}


//
// Callback function for HID application
//
void usbHidAppPoll(void) {

    //
    // Output keyboard LED status on LEDs 2-4
    //
    // if (hidData.keyboardOutReport.ledStatus & 0x01)
    // {
    //     bspLedSet(BSP_LED_2);
    // }
    // else
    // {
    //     bspLedClear(BSP_LED_2);
    // }
    // if (hidData.keyboardOutReport.ledStatus & 0x02)
    // {
    //     bspLedSet(BSP_LED_3);
    // }
    // else
    // {
    //     bspLedClear(BSP_LED_3);
    // }
    // if (hidData.keyboardOutReport.ledStatus & 0x04)
    // {
    //     bspLedSet(BSP_LED_4);
    // }
    // else
    // {
    //     bspLedClear(BSP_LED_4);
    // }
}
