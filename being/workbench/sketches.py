being <<<


def value_outputs(blocks):
    for block in blocks:
        yield from filter_by_type(block.outputs, ValueOutput)

def value_inputs(blocks):
    for block in blocks:
        yield from filter_by_type(block.inputs, ValueInput)

def message_outputs(blocks):
    for block in blocks:
        yield from filter_by_type(block.outputs, MessageOutput)

def message_inputs(blocks):
    for block in blocks:
        yield from filter_by_type(block.inputs, MessageInput)


def assign_ids(things):
    """Enumerate things and return thing <-> id mappings."""
    mapping = dict(enumerate(things))
    backmapping = {thing: id for id, thing in mapping.items()}
    return mapping, backmapping



        self.valueOutputs = list(value_outputs(self.execOrder))
        self.valueInputs = list(value_inputs(self.execOrder))
        self.messageOutputs = list(message_outputs(self.execOrder))
        self.messageInputs = list(message_inputs(self.execOrder))


        # Create block ids
        self.id2block, self.block2id = assign_ids(self.execOrder)
        self.id2valueOutputs, self.valueOutputs2id = assign_ids(self.valueOutputs)
        self.id2valueInputs, self.valueInputs2id = assign_ids(self.valueInputs)
        self.id2messageOutputs, self.messageOutputs2id = assign_ids(self.messageOutputs)
        self.id2messageInputs, self.messageInputs2id = assign_ids(self.messageInputs)



    def get_id(self, thing):
        if isinstance(thing, Block):
            return self.block2id[thing]
        if isinstance(thing, ValueOutput):
            return self.valueOutputs2id[thing]
    def capture_value_outputs(self):
        """Grab current state of all value outputs."""
        return [out.value for out in self.valueOutputs]



server api <<<



def init_api() -> web.Application:
    """Create an application object which handles all API calls."""
    routes = web.RouteTableDef()

    @routes.get('/hello')
    async def say_hello(request: web.Request):
        if 'name' in request.query:
            return web.json_response(
                f"Hello {request.query['name']}"
            )
        else:
            return web.json_response('Hello world')

    @routes.get('/graph')
    async def get_graph(request: web.Request):
        raise web.HTTPNotImplemented()

    @routes.get('/blocks')
    async def get_blocks(request: web.Request):
        if 'type' in request.query:
            raise web.HTTPNotImplemented()
        else:
            raise web.HTTPNotImplemented()

    @routes.get('/blocks/{id}')
    async def get_block(request: web.Request):
        return web.json_response(f"TODO: return {request.match_info['id']}")

    @routes.put('/blocks/{id}')
    async def update_block(request: web.Request):
        try:
            data = await request.json()
            # TODO : update block
            return await get_block(request)
        except json.decoder.JSONDecodeError:
            raise web.HTTPBadRequest()

    @routes.get('/connections')
    async def get_connections(request: web.Request):
        raise web.HTTPNotImplemented()

    @routes.get('/state')
    async def get_state(request: web.Request):
        return web.json_response('stopped')

    @routes.put('/state')
    async def set_state(request: web.Request):
        try:
            reqState = await request.json()
            reqState = reqState.upper()

            # TODO : set states
            if reqState == 'RUN':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('RUNNING')
                except Exception as e:
                    return web.HTTPInternalServerError(reason=e)

            elif reqState == 'PAUSE':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('PAUSED')
                except Exception as e:
                    return web.HTTPInternalServerError(reason=e)

            elif reqState == 'STOP':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('STOPPED')
                except Exception as e:
                    return web.HTTPInternalServerError(reason=e)

            else:
                raise web.HTTPBadRequest()

        except json.decoder.JSONDecodeError:
            raise web.HTTPBadRequest()

    @routes.get('/block-network/state')
    async def get_block_network_state(request: web.Request):
        raise web.HTTPNotImplemented()

    api = web.Application()
    api.add_routes(routes)
    return api


