################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (11.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Middlewares/ST/AI/Npu/Devices/STM32N6XX/mcu_cache.c \
../Middlewares/ST/AI/Npu/Devices/STM32N6XX/npu_cache.c 

OBJS += \
./Middlewares/ST/AI/Npu/Devices/STM32N6XX/mcu_cache.o \
./Middlewares/ST/AI/Npu/Devices/STM32N6XX/npu_cache.o 

C_DEPS += \
./Middlewares/ST/AI/Npu/Devices/STM32N6XX/mcu_cache.d \
./Middlewares/ST/AI/Npu/Devices/STM32N6XX/npu_cache.d 


# Each subdirectory must supply rules for building sources it contributes
Middlewares/ST/AI/Npu/Devices/STM32N6XX/%.o Middlewares/ST/AI/Npu/Devices/STM32N6XX/%.su Middlewares/ST/AI/Npu/Devices/STM32N6XX/%.cyclo: ../Middlewares/ST/AI/Npu/Devices/STM32N6XX/%.c Middlewares/ST/AI/Npu/Devices/STM32N6XX/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F469xx -c -I../Core/Inc -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Lib" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI/Runtime" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI/Runtime/Inc" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Src/AI" -I../Utilities/Fonts -I../Drivers/BSP/STM32469I-Discovery -I../Drivers/BSP/Components -I../FATFS/Target -I../FATFS/App -I../USB_HOST/App -I../USB_HOST/Target -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Middlewares/Third_Party/FreeRTOS/Source/include -I../Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS -I../Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM4F -I../Middlewares/Third_Party/FatFs/src -I../Middlewares/ST/STM32_USB_Host_Library/Core/Inc -I../Middlewares/ST/STM32_USB_Host_Library/Class/CDC/Inc -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Middlewares-2f-ST-2f-AI-2f-Npu-2f-Devices-2f-STM32N6XX

clean-Middlewares-2f-ST-2f-AI-2f-Npu-2f-Devices-2f-STM32N6XX:
	-$(RM) ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/mcu_cache.cyclo ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/mcu_cache.d ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/mcu_cache.o ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/mcu_cache.su ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/npu_cache.cyclo ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/npu_cache.d ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/npu_cache.o ./Middlewares/ST/AI/Npu/Devices/STM32N6XX/npu_cache.su

.PHONY: clean-Middlewares-2f-ST-2f-AI-2f-Npu-2f-Devices-2f-STM32N6XX

