# coding: utf-8

"""Get data from local ZeroTier node using async client session."""
import asyncio
import aiohttp
import logging

from diskcache import Index
from ztcli_api import ZeroTier
from ztcli_api import ZeroTierConnectionError

from node_tools.async_funcs import add_network_object
from node_tools.async_funcs import get_network_object_data
from node_tools.async_funcs import get_network_object_ids
from node_tools.cache_funcs import find_keys
from node_tools.cache_funcs import get_net_status
from node_tools.cache_funcs import get_peer_status
from node_tools.cache_funcs import handle_node_status
from node_tools.cache_funcs import load_cache_by_type
from node_tools.helper_funcs import NODE_SETTINGS
from node_tools.helper_funcs import get_cachedir
from node_tools.helper_funcs import get_token
from node_tools.node_funcs import get_ztcli_data


logger = logging.getLogger('nodestate')


async def main():
    """State cache updater to retrieve data from a local ZeroTier node."""
    async with aiohttp.ClientSession() as session:
        ZT_API = get_token()
        client = ZeroTier(ZT_API, loop, session)

        try:
            # get status details of the local node and update state
            await client.get_data('status')
            node_id = handle_node_status(client.data, cache)

            if NODE_SETTINGS['mode'] == 'peer':
                # get status details of the node peers
                await client.get_data('peer')
                peer_data = client.data
                logger.info('Found {} peers'.format(len(peer_data)))
                peer_keys = find_keys(cache, 'peer')
                logger.debug('Returned peer keys: {}'.format(peer_keys))
                load_cache_by_type(cache, peer_data, 'peer')

                # check for moon data (only exists for moons we orbit)
                moon_data = get_ztcli_data(action='listmoons')
                if moon_data:
                    load_cache_by_type(cache, moon_data, 'moon')

                moonStatus = []
                peerStatus = get_peer_status(cache)
                for peer in peerStatus:
                    if peer['role'] == 'MOON':
                        moonStatus.append(peer)
                        break
                logger.debug('Got moon state: {}'.format(moonStatus))
                load_cache_by_type(cache, moonStatus, 'mstate')

            # get all available network data
            await client.get_data('network')
            net_data = client.data
            logger.info('Found {} networks'.format(len(net_data)))
            net_keys = find_keys(cache, 'net')
            logger.debug('Returned network keys: {}'.format(net_keys))
            load_cache_by_type(cache, net_data, 'net')

            netStatus = get_net_status(cache)
            logger.debug('Got net state: {}'.format(netStatus))
            load_cache_by_type(cache, netStatus, 'istate')
            if NODE_SETTINGS['mode'] == 'adhoc' and not NODE_SETTINGS['nwid']:
                NODE_SETTINGS['nwid'] = netStatus[0]['identity']

        except Exception as exc:
            logger.error(str(exc))
            raise exc


cache = Index(get_cachedir())
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
