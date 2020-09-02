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

from typing import BinaryIO, Dict, Any, List
from bson import ObjectId
from io import BytesIO
from copy import deepcopy

from superdesk.services import Service
from superdesk.storage.mimetype_mixin import MimetypeMixin

from sams.factory.service import SamsService
from sams.sets import get_service
from sams_client.errors import SamsAssetErrors


class AssetsService(SamsService, MimetypeMixin):
    def post(self, docs: List[Dict[str, Any]], **kwargs) -> List[ObjectId]:
        """Uploads binary and stores metadata

        :param docs: An array of metadata & binaries to create
        :param kwargs: Dictionary containing the keyword arguments
        :return: list of generated IDs for the new documents
        :rtype: list[bson.objectid.ObjectId]
        """

        for doc in docs:
            content = doc.pop('binary', None)

            if not content:
                raise SamsAssetErrors.BinaryNotSupplied()

            self.validate_post(doc)
            file_meta = self.upload_binary(doc, content)
            doc.update(file_meta)

        return super(Service, self).post(docs, **kwargs)

    def patch(self, id: ObjectId, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates the binary and/or metadata

        .. note::
            When uploading a new binary to an existing Asset, the original binary
            will be deleted from the StorageDestination.

        :param bson.objectid.ObjectId id: ID for the Asset
        :param dict updates: Dictionary containing the desired metadata/binary to update
        :return: Dictionary containing the updated attributes of the Asset
        :rtype: dict
        """

        original = self.get_by_id(id)
        content = updates.pop('binary', None)
        self.validate_patch(original, updates)

        if content:
            asset = deepcopy(original)
            asset.update(updates)

            # Force mimetype from provided updates, if any
            asset['mimetype'] = updates.get('mimetype')

            file_meta = self.upload_binary(asset, content)
            updates.update(file_meta)

        return super(Service, self).patch(id, updates)

    def on_deleted(self, doc: Dict[str, Any]):
        """Delete the Asset Binary after the Metadata is deleted

        :param dict doc: The Asset that was deleted
        """

        if doc.get('_media_id'):
            set_service = get_service()
            provider = set_service.get_provider_instance(doc.get('set_id'))
            provider.delete(doc['_media_id'])

    def upload_binary(self, asset: Dict[str, Any], content: BinaryIO or bytes, delete_original: bool = True) -> dict:
        """Uploads binary data for provided Asset

        :param dict asset: The Asset Metadata used to store the binary for
        :param io.BytesIO content: The Asset Binary to upload
        :param bool delete_original: If ``True``, deletes the existing binary (if any)
        :return: Returns the ``_media_id``, ``length`` and ``mimetype`` attributes of the binary
        :rtype: dict
        """

        set_id = asset.get('set_id')
        filename = asset.get('filename')
        mimetype = asset.get('mimetype')

        try:
            content.seek(0)
        except AttributeError:
            content = BytesIO(content)

        set_service = get_service()
        provider = set_service.get_provider_instance(set_id)
        media_id = provider.put(content, filename)
        content.seek(0)

        asset_binary = provider.get(media_id)

        if delete_original and asset.get('_media_id'):
            provider.delete(asset['_media_id'])

        return {
            'binary': media_id,
            '_media_id': media_id,
            'length': asset_binary.length,
            'mimetype': self._get_mimetype(asset_binary, filename, mimetype)
        }

    def download_binary(self, asset_id: ObjectId) -> BinaryIO:
        """Downloads the Asset Binary

        :param bson.objectid.ObjectId asset_id: The ID of the Asset
        :return: The Binary Stream for the Asset Binary
        :rtype: io.BytesIO
        """

        asset = self.get_by_id(asset_id)
        if not asset:
            raise SamsAssetErrors.AssetNotFound(asset_id)

        set_service = get_service()
        provider = set_service.get_provider_instance(asset.get('set_id'))
        return provider.get(asset.get('_media_id'))
