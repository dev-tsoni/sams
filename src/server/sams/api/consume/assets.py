#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of SAMS.
#
# Copyright 2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""The Assets Consume API allows to search Assets.

This service and resource is intended to be used by external clients.
To access Assets inside the SAMS application, use the :mod:`sams.assets` module instead

=====================   =========================================================
**endpoint name**        'consume_assets'
**resource title**       'Asset'
**resource url**         [GET] '/consume/assets'
**item url**             [GET] '/consume/assets/<:class:`~bson.objectid.ObjectId`>'
**schema**               :attr:`sams_client.schemas.assets.ASSET_SCHEMA`
=====================   =========================================================
"""
import superdesk
from flask import request, current_app as app
from sams.api.service import SamsApiService
from sams.assets import get_service as get_asset_service
from sams_client.schemas import ASSET_SCHEMA
from sams.logging import logger
from superdesk.resource import Resource, build_custom_hateoas
from werkzeug.wsgi import wrap_file


assets_bp = superdesk.Blueprint('assets', __name__)


@assets_bp.route('/consume/assets/binary/<asset_id>', methods=['GET'])
def download_binary(asset_id):
    """
    Uses asset_id and returns the corresponding
    asset binary
    """
    service = get_asset_service()
    file = service.download_binary(asset_id)
    data = wrap_file(request.environ, file, buffer_size=1024 * 256)
    response = app.response_class(
        data,
        mimetype=file.content_type,
        direct_passthrough=True
    )
    return response


class ConsumeAssetResource(Resource):
    endpoint_name = 'consume_assets'
    resource_title = 'Asset'
    url = 'consume/assets'
    item_methods = ['GET']
    resource_methods = ['GET']
    schema = ASSET_SCHEMA


class ConsumeAssetService(SamsApiService):
    def on_fetched_item(self, doc):
        self.enhance_items([doc])

    def on_fetched(self, doc):
        self.enhance_items(doc['_items'])

    def enhance_items(self, docs):
        for doc in docs:
            build_custom_hateoas(
                {
                    'self': {
                        'title': ConsumeAssetResource.resource_title,
                        'href': ConsumeAssetResource.url + '/{_id}'
                    }
                },
                doc,
                _id=str(doc.get('_id'))
            )
