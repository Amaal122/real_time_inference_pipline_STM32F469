#include "ff_gen_drv.h"
#include "sd_diskio.h"
#include <string.h>
#include <stdint.h>

/* Private defines -----------------------------------------------------------*/

#define SD_TIMEOUT              30000U
#define SD_DEFAULT_BLOCK_SIZE   512U

/* Disk status */
static volatile DSTATUS Stat = STA_NOINIT;

/* Private function prototypes -----------------------------------------------*/

static DSTATUS SD_CheckStatus(BYTE lun);
static int SD_CheckStatusWithTimeout(uint32_t timeout);

DSTATUS SD_initialize(BYTE);
DSTATUS SD_status(BYTE);
DRESULT SD_read(BYTE, BYTE*, DWORD, UINT);

#if _USE_WRITE == 1
DRESULT SD_write(BYTE, const BYTE*, DWORD, UINT);
#endif

#if _USE_IOCTL == 1
DRESULT SD_ioctl(BYTE, BYTE, void*);
#endif

/* Disk driver structure -----------------------------------------------------*/

const Diskio_drvTypeDef SD_Driver =
{
    SD_initialize,
    SD_status,
    SD_read,

#if _USE_WRITE == 1
    SD_write,
#endif

#if _USE_IOCTL == 1
    SD_ioctl,
#endif
};


/* Private functions ---------------------------------------------------------*/

/**
  * @brief  Wait until SD card is ready.
  */
static int SD_CheckStatusWithTimeout(uint32_t timeout)
{
    uint32_t timer = HAL_GetTick();

    while ((HAL_GetTick() - timer) < timeout)
    {
        if (BSP_SD_GetCardState() == SD_TRANSFER_OK)
        {
            return 0;
        }
    }

    return -1;
}


/**
  * @brief  Check SD card status.
  */
static DSTATUS SD_CheckStatus(BYTE lun)
{
    (void)lun;

    Stat = STA_NOINIT;

    if (BSP_SD_GetCardState() == SD_TRANSFER_OK)
    {
        Stat &= ~STA_NOINIT;
    }

    return Stat;
}


/**
  * @brief  Initializes a Drive
  */
DSTATUS SD_initialize(BYTE lun)
{
    (void)lun;

    Stat = STA_NOINIT;

    if (BSP_SD_Init() == MSD_OK)
    {
        if (BSP_SD_GetCardState() == SD_TRANSFER_OK)
        {
            Stat &= ~STA_NOINIT;
        }
    }

    return Stat;
}


/**
  * @brief  Gets Disk Status
  */
DSTATUS SD_status(BYTE lun)
{
    return SD_CheckStatus(lun);
}


/**
  * @brief  Reads Sector(s)
  */
DRESULT SD_read(BYTE lun, BYTE *buff, DWORD sector, UINT count)
{
    (void)lun;

    DRESULT res = RES_ERROR;

    /* Wait for SD card to be ready */
    if (SD_CheckStatusWithTimeout(SD_TIMEOUT) < 0)
    {
        return RES_NOTRDY;
    }

    /* Start DMA read */
    if (BSP_SD_ReadBlocks_DMA(
            (uint32_t *)buff,
            (uint32_t)sector,
            (uint32_t)count) != MSD_OK)
    {
        return RES_ERROR;
    }

    /* Wait for DMA transfer to finish */
    if (SD_CheckStatusWithTimeout(SD_TIMEOUT) == 0)
    {
        res = RES_OK;
    }

    return res;
}


/**
  * @brief  Writes Sector(s)
  */
#if _USE_WRITE == 1

DRESULT SD_write(BYTE lun,
                 const BYTE *buff,
                 DWORD sector,
                 UINT count)
{
    (void)lun;

    DRESULT res = RES_ERROR;

    /* Wait for SD card to be ready */
    if (SD_CheckStatusWithTimeout(SD_TIMEOUT) < 0)
    {
        return RES_NOTRDY;
    }

    /* Start DMA write */
    if (BSP_SD_WriteBlocks_DMA(
            (uint32_t *)buff,
            (uint32_t)sector,
            (uint32_t)count) != MSD_OK)
    {
        return RES_ERROR;
    }

    /* Wait for DMA transfer to finish */
    if (SD_CheckStatusWithTimeout(SD_TIMEOUT) == 0)
    {
        res = RES_OK;
    }

    return res;
}

#endif /* _USE_WRITE == 1 */


/**
  * @brief  I/O control operation
  */
#if _USE_IOCTL == 1

DRESULT SD_ioctl(BYTE lun, BYTE cmd, void *buff)
{
    (void)lun;

    DRESULT res = RES_ERROR;
    BSP_SD_CardInfo CardInfo;

    if (Stat & STA_NOINIT)
    {
        return RES_NOTRDY;
    }

    switch (cmd)
    {
        case CTRL_SYNC:
            res = RES_OK;
            break;

        case GET_SECTOR_COUNT:

            BSP_SD_GetCardInfo(&CardInfo);

            *(DWORD *)buff = CardInfo.LogBlockNbr;

            res = RES_OK;
            break;

        case GET_SECTOR_SIZE:

            BSP_SD_GetCardInfo(&CardInfo);

            *(WORD *)buff = CardInfo.LogBlockSize;

            res = RES_OK;
            break;

        case GET_BLOCK_SIZE:

            BSP_SD_GetCardInfo(&CardInfo);

            *(DWORD *)buff =
                CardInfo.LogBlockSize / SD_DEFAULT_BLOCK_SIZE;

            res = RES_OK;
            break;

        default:

            res = RES_PARERR;
            break;
    }

    return res;
}

#endif /* _USE_IOCTL == 1 */
