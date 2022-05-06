#ifndef MEDIA__RPC_CFG_PARSER_H
#define MEDIA__RPC_CFG_PARSER_H
#ifdef __cplusplus
extern "C" {
#endif

#include "app.h"
#include "rpc/datatypes.h"

int app_rpc_cfg_deinit(arpc_cfg_t *cfg);

int parse_cfg_rpc_caller(json_t *objs, app_cfg_t *app_cfg);

int parse_cfg_rpc_callee(json_t *objs, app_cfg_t *app_cfg);

#ifdef __cplusplus
} // end of extern C clause
#endif
#endif // end of MEDIA__RPC_CFG_PARSER_H
