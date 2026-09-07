################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (11.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Middlewares/ST/AI/Misc/Src/aiTestHelper.c \
../Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.c \
../Middlewares/ST/AI/Misc/Src/aiTestUtility.c \
../Middlewares/ST/AI/Misc/Src/ai_device_adaptor.c \
../Middlewares/ST/AI/Misc/Src/lc_print.c \
../Middlewares/ST/AI/Misc/Src/syscalls.c 

OBJS += \
./Middlewares/ST/AI/Misc/Src/aiTestHelper.o \
./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.o \
./Middlewares/ST/AI/Misc/Src/aiTestUtility.o \
./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.o \
./Middlewares/ST/AI/Misc/Src/lc_print.o \
./Middlewares/ST/AI/Misc/Src/syscalls.o 

C_DEPS += \
./Middlewares/ST/AI/Misc/Src/aiTestHelper.d \
./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.d \
./Middlewares/ST/AI/Misc/Src/aiTestUtility.d \
./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.d \
./Middlewares/ST/AI/Misc/Src/lc_print.d \
./Middlewares/ST/AI/Misc/Src/syscalls.d 


# Each subdirectory must supply rules for building sources it contributes
Middlewares/ST/AI/Misc/Src/%.o Middlewares/ST/AI/Misc/Src/%.su Middlewares/ST/AI/Misc/Src/%.cyclo: ../Middlewares/ST/AI/Misc/Src/%.c Middlewares/ST/AI/Misc/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F469xx -c -I../Core/Inc -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Lib" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI/Runtime" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI/Runtime/Inc" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Src/AI" -I../Utilities/Fonts -I../Drivers/BSP/STM32469I-Discovery -I../Drivers/BSP/Components -I../FATFS/Target -I../FATFS/App -I../USB_HOST/App -I../USB_HOST/Target -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Middlewares/Third_Party/FreeRTOS/Source/include -I../Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS -I../Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM4F -I../Middlewares/Third_Party/FatFs/src -I../Middlewares/ST/STM32_USB_Host_Library/Core/Inc -I../Middlewares/ST/STM32_USB_Host_Library/Class/CDC/Inc -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Middlewares-2f-ST-2f-AI-2f-Misc-2f-Src

clean-Middlewares-2f-ST-2f-AI-2f-Misc-2f-Src:
	-$(RM) ./Middlewares/ST/AI/Misc/Src/aiTestHelper.cyclo ./Middlewares/ST/AI/Misc/Src/aiTestHelper.d ./Middlewares/ST/AI/Misc/Src/aiTestHelper.o ./Middlewares/ST/AI/Misc/Src/aiTestHelper.su ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.cyclo ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.d ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.o ./Middlewares/ST/AI/Misc/Src/aiTestHelper_ST_AI.su ./Middlewares/ST/AI/Misc/Src/aiTestUtility.cyclo ./Middlewares/ST/AI/Misc/Src/aiTestUtility.d ./Middlewares/ST/AI/Misc/Src/aiTestUtility.o ./Middlewares/ST/AI/Misc/Src/aiTestUtility.su ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.cyclo ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.d ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.o ./Middlewares/ST/AI/Misc/Src/ai_device_adaptor.su ./Middlewares/ST/AI/Misc/Src/lc_print.cyclo ./Middlewares/ST/AI/Misc/Src/lc_print.d ./Middlewares/ST/AI/Misc/Src/lc_print.o ./Middlewares/ST/AI/Misc/Src/lc_print.su ./Middlewares/ST/AI/Misc/Src/syscalls.cyclo ./Middlewares/ST/AI/Misc/Src/syscalls.d ./Middlewares/ST/AI/Misc/Src/syscalls.o ./Middlewares/ST/AI/Misc/Src/syscalls.su

.PHONY: clean-Middlewares-2f-ST-2f-AI-2f-Misc-2f-Src

