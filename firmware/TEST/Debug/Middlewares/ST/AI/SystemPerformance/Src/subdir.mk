################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (11.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance.c \
../Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_RELOC.c \
../Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_ST_AI.c \
../Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_TFLM.c 

OBJS += \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance.o \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_RELOC.o \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_ST_AI.o \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_TFLM.o 

C_DEPS += \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance.d \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_RELOC.d \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_ST_AI.d \
./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_TFLM.d 


# Each subdirectory must supply rules for building sources it contributes
Middlewares/ST/AI/SystemPerformance/Src/%.o Middlewares/ST/AI/SystemPerformance/Src/%.su Middlewares/ST/AI/SystemPerformance/Src/%.cyclo: ../Middlewares/ST/AI/SystemPerformance/Src/%.c Middlewares/ST/AI/SystemPerformance/Src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m4 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F469xx -c -I../Core/Inc -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Lib" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI/Runtime" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Inc/AI/Runtime/Inc" -I"C:/Users/bougu/STM32CubeIDE/workspace_1.14.0/NILMstage/TEST/Core/Src/AI" -I../Utilities/Fonts -I../Drivers/BSP/STM32469I-Discovery -I../Drivers/BSP/Components -I../FATFS/Target -I../FATFS/App -I../USB_HOST/App -I../USB_HOST/Target -I../Drivers/STM32F4xx_HAL_Driver/Inc -I../Drivers/STM32F4xx_HAL_Driver/Inc/Legacy -I../Middlewares/Third_Party/FreeRTOS/Source/include -I../Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS -I../Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM4F -I../Middlewares/Third_Party/FatFs/src -I../Middlewares/ST/STM32_USB_Host_Library/Core/Inc -I../Middlewares/ST/STM32_USB_Host_Library/Class/CDC/Inc -I../Drivers/CMSIS/Device/ST/STM32F4xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb -o "$@"

clean: clean-Middlewares-2f-ST-2f-AI-2f-SystemPerformance-2f-Src

clean-Middlewares-2f-ST-2f-AI-2f-SystemPerformance-2f-Src:
	-$(RM) ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance.cyclo ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance.d ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance.o ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance.su ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_RELOC.cyclo ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_RELOC.d ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_RELOC.o ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_RELOC.su ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_ST_AI.cyclo ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_ST_AI.d ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_ST_AI.o ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_ST_AI.su ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_TFLM.cyclo ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_TFLM.d ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_TFLM.o ./Middlewares/ST/AI/SystemPerformance/Src/aiSystemPerformance_TFLM.su

.PHONY: clean-Middlewares-2f-ST-2f-AI-2f-SystemPerformance-2f-Src

