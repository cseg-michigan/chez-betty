PROJECT_NAME = $(shell basename "$(realpath ./)")

APPLICATION_SRCS = $(notdir $(wildcard ./*.c))
APPLICATION_SRCS += cpu.c
APPLICATION_SRCS += bsp.c
APPLICATION_SRCS += bsp_led.c
APPLICATION_SRCS += adc.c
APPLICATION_SRCS += gpio.c
APPLICATION_SRCS += interrupt.c
APPLICATION_SRCS += sys_ctrl.c
APPLICATION_SRCS += ioc.c
APPLICATION_SRCS += gptimer.c

APPLICATION_SRCS += usb.c
APPLICATION_SRCS += usb_suspend.c
APPLICATION_SRCS += usb_framework.c
APPLICATION_SRCS += usb_interrupt.c
APPLICATION_SRCS += usb_standard_requests.c
APPLICATION_SRCS += usb_descriptor_parser.c
APPLICATION_SRCS += usb_in_buffer.c
APPLICATION_SRCS += usb_out_buffer.c

APPLICATION_SRCS += usb_hid.c
APPLICATION_SRCS += usb_hid_reports.c

APPLICATION_SRCS += usb_cdc.c
APPLICATION_SRCS += usb_cdc_hooks.c

APPLICATION_SRCS += app_usb_descriptor.c

CC2538_BASE_PATH ?= ../../cc2538-base

LIBRARY_PATHS += $(CC2538_BASE_PATH)/platforms/atum
SOURCE_PATHS += $(CC2538_BASE_PATH)/platforms/atum

LIBRARY_PATHS += . $(CC2538_BASE_PATH)/include
SOURCE_PATHS += $(CC2538_BASE_PATH)/src

include $(CC2538_BASE_PATH)/make/Makefile
