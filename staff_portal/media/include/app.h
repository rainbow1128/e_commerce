#ifndef MEIDA__APP_H
#define MEIDA__APP_H
#ifdef __cplusplus
extern "C" {
#endif

#include "datatypes.h"

#define APP_DEFAULT_MAX_CONNECTIONS 1024

#ifdef TCP_FASTOPEN
#define APP_DEFAULT_LENGTH_TCP_FASTOPEN_QUEUE  150
#else
#define APP_DEFAULT_LENGTH_TCP_FASTOPEN_QUEUE  0
#endif


int start_application(const char *cfg_file_path, const char *exe_path);

int init_security(void);

int app_server_ready(void);

const app_cfg_t *app_get_global_cfg(void);

void  app_global_cfg_set_exepath(const char *exe_path);

#ifdef __cplusplus
} // end of extern C clause
#endif 
#endif // end of MEIDA__APP_H
