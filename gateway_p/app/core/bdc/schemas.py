"""
Schemas para integración con Banco de Comercio (BDC)
"""
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict


# ============= Autenticación BDC =============

class BDCAuthRequest(BaseModel):
    """Schema para request de autenticación con BDC"""
    clientId: str = Field(..., description="ID del cliente BDC")
    clientSecret: str = Field(..., description="Secret del cliente BDC")


class BDCAuthResponse(BaseModel):
    """Schema para response de autenticación de BDC"""
    accessToken: str = Field(..., description="Token de acceso JWT")
    expiresIn: int = Field(..., description="Tiempo de expiración en segundos")


class BDCAuthData(BaseModel):
    """Schema para datos de autenticación de BDC"""
    accessToken: str
    expiresIn: int


class BDCResponse(BaseModel):
    """Schema genérico para respuestas de BDC API"""
    model_config = ConfigDict(extra="allow")
    
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos de respuesta")
    time: Optional[str] = Field(None, description="Timestamp del servidor")

class BDCAuthFullResponse(BDCResponse):
    """Schema completo para respuesta de autenticación BDC"""
    data: Optional[BDCAuthData] = None


# ============= Alias =============

class BDCAliasLookupRequest(BaseModel):
    """Schema para request de consulta de alias"""
    tipoConsulta: str = Field("ALIAS", description="Tipo de consulta (por defecto: ALIAS)")
    valorConsulta: str = Field(..., description="Valor del alias a consultar")


class BDCAliasCreateRequest(BaseModel):
    """Schema para request de alta/creacion de alias"""
    cuitTitular: str = Field(..., description="CUIT del titular")
    cbuCuenta: str = Field(..., description="CBU de la cuenta")
    valorAliasCVU: str = Field(..., description="Nuevo alias a registrar")


class BDCAliasEditRequest(BaseModel):
    """Schema para request de edicion de alias"""
    cuitTitular: Optional[str] = Field(None, description="CUIT del titular")
    cbuCuenta: Optional[str] = Field(None, description="CBU de la cuenta")
    aliasNuevo: Optional[str] = Field(None, description="Nuevo alias a registrar")
    aliasAnterior: Optional[str] = Field(None, description="Alias actual a reemplazar")
    accountLabel: Optional[str] = Field(
        None,
        description="Campo del endpoint PATCH /sub-account/{cvu}. Si se usa, debe invocar ese endpoint.",
    )


class BDCAliasRemoveRequest(BaseModel):
    """Schema para request de eliminacion de alias"""
    cuitTitular: str = Field(..., description="CUIT del titular")
    cbuCuenta: str = Field(..., description="CBU de la cuenta")
    valorAliasCVU: str = Field(..., description="Alias a eliminar")


# ============= Informacion Personal =============

class BDCGetEntityRequest(BaseModel):
    """Schema para request de informacion de entidad"""
    addressType: str = Field(..., description="Tipo de direccion: CBU_CVU, ALIAS, etc.")
    address: str = Field(..., description="CBU/CVU o Alias de la cuenta")


# ============= Transferencias =============

class BDCOwner(BaseModel):
    """Información del propietario de la cuenta"""
    personIdType: str = Field(..., description="Tipo de identificación: CUI, DNI, CUIT, etc.")
    personId: str = Field(..., description="Número de identificación")


class BDCAccountInfo(BaseModel):
    """Información de cuenta para transferencias"""
    addressType: str = Field(..., description="Tipo de dirección: CBU_CVU, ALIAS, etc.")
    address: str = Field(..., description="CBU/CVU o Alias")
    owner: BDCOwner = Field(..., description="Propietario de la cuenta")


class BDCTransferBody(BaseModel):
    """Cuerpo de transferencia"""
    currencyId: str = Field(..., description="Código de moneda: 032=ARS, 840=USD")
    amount: float = Field(..., description="Monto a transferir")
    description: str = Field(..., description="Descripción de la transferencia")
    concept: str = Field(..., description="Concepto: VAR, ALQ, CUO, etc.")


class BDCTransferRequest(BaseModel):
    """Schema para request de transferencia en BDC"""
    model_config = {"populate_by_name": True, "json_schema_mode": "serialization"}
    
    originId: Optional[str] = Field(
        None,
        description="ID único de la transferencia generado por el cliente",
        json_schema_extra={"position": 0},
    )
    from_: BDCAccountInfo = Field(..., alias="from", serialization_alias="from", description="Cuenta origen", json_schema_extra={"position": 1})
    to: BDCAccountInfo = Field(..., description="Cuenta destino", json_schema_extra={"position": 2})
    body: BDCTransferBody = Field(..., description="Detalles de la transferencia", json_schema_extra={"position": 3})


class BDCTransferRequestInput(BaseModel):
    """Schema para input de transferencia (sin originId, se genera en BD)"""
    model_config = {"populate_by_name": True}
    
    from_: BDCAccountInfo = Field(..., alias="from", description="Cuenta origen")
    to: BDCAccountInfo = Field(..., description="Cuenta destino")
    body: BDCTransferBody = Field(..., description="Detalles de la transferencia")


class BDCTransferRequestSimpleInput(BaseModel):
    """Schema simplificado para input de transferencia desde la APP (solo datos esenciales)"""
    originCbuCvu: str = Field(..., min_length=22, max_length=22, description="CBU/CVU origen de 22 dígitos")
    destinationCbuCvu: str = Field(..., min_length=22, max_length=22, description="CBU/CVU destino de 22 dígitos")
    amount: float = Field(..., gt=0, description="Monto a transferir (debe ser mayor a 0)")
    description: str = Field(default="Transferencia", max_length=255, description="Descripción de la transferencia")
    concept: str = Field(default="VAR", max_length=3, description="Concepto: VAR, ALQ, CUO, etc.")
    currencyId: str = Field(default="032", description="Código de moneda: 032=ARS, 840=USD")

    model_config = ConfigDict(populate_by_name=True)


class BDCTransferSuccessResponse(BaseModel):
    """Schema para respuesta exitosa de transferencia - Permite campos extra del banco"""
    model_config = ConfigDict(extra="allow")
    
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    message: Optional[str] = Field(None, description="Mensaje descriptivo")
    time: Optional[str] = Field(None, description="Timestamp del servidor BDC")


# ============= Consulta de Transferencias =============

class BDCTransferRequestData(BaseModel):
    """Datos del request original de la transferencia"""
    originId: Any = Field(..., description="ID único de la transferencia")
    from_: Optional[BDCAccountInfo] = Field(None, alias="from", serialization_alias="from")
    to: Optional[BDCAccountInfo] = None
    body: Optional[BDCTransferBody] = None
    
    class Config:
        populate_by_name = True
        extra = "allow"  # Permite campos adicionales


class BDCRespuesta(BaseModel):
    """Respuesta del banco"""
    codigo: Optional[str] = Field(None, description="Código de respuesta")
    descripcion: Optional[str] = Field(None, description="Descripción de la respuesta")
    
    class Config:
        extra = "allow"


class BDCCuenta(BaseModel):
    """Información de cuenta bancaria"""
    cbu: Optional[str] = Field(None, description="CBU de la cuenta")
    
    class Config:
        extra = "allow"


class BDCCredito(BaseModel):
    """Información de crédito"""
    cuit: Optional[str] = Field(None, description="CUIT del destinatario")
    banco: Optional[str] = Field(None, description="Código del banco")
    sucursal: Optional[str] = Field(None, description="Código de sucursal")
    cuenta: Optional[BDCCuenta] = Field(None, description="Información de cuenta")
    
    class Config:
        extra = "allow"


class BDCImporte(BaseModel):
    """Información del importe"""
    moneda: Optional[str] = Field(None, description="Código de moneda")
    importe: Optional[float] = Field(None, description="Monto transferido")
    
    class Config:
        extra = "allow"


class BDCObjetoEstado(BaseModel):
    """Estado del objeto de transferencia"""
    codigo: Optional[str] = Field(None, description="Código de estado")
    descripcion: Optional[str] = Field(None, description="Descripción del estado")
    
    class Config:
        extra = "allow"


class BDCObjeto(BaseModel):
    """Objeto de transferencia"""
    tipo: Optional[str] = Field(None, description="Tipo de objeto")
    id: Optional[str] = Field(None, description="ID del objeto")
    estado: Optional[BDCObjetoEstado] = Field(None, description="Estado del objeto")
    
    class Config:
        extra = "allow"


class BDCEvaluacion(BaseModel):
    """Evaluación de la transferencia"""
    puntaje: Optional[int] = Field(None, description="Puntaje de evaluación")
    reglas: Optional[str] = Field(None, description="Reglas aplicadas")
    
    class Config:
        extra = "allow"


class BDCTransferResponseData(BaseModel):
    """Datos de respuesta detallada de BDC"""
    respuesta: Optional[BDCRespuesta] = None
    credito: Optional[BDCCredito] = None
    importe: Optional[BDCImporte] = None
    fechaHoraEjecucion: Optional[str] = Field(None, description="Fecha y hora de ejecución")
    fechaNegocio: Optional[str] = Field(None, description="Fecha de negocio")
    dest_trx: Optional[str] = Field(None, description="ID de transacción destino")
    dest_terminal: Optional[str] = Field(None, description="Terminal destino")
    dest_adicional: Optional[str] = Field(None, description="Información adicional")
    dest_ori_trx_id: Optional[int] = Field(None, description="ID original de transacción")
    objeto: Optional[BDCObjeto] = Field(None, description="Objeto de transferencia")
    evaluacion: Optional[BDCEvaluacion] = Field(None, description="Evaluación de la transferencia")
    time: Optional[str] = Field(None, description="Timestamp de la respuesta BDC")
    
    class Config:
        extra = "allow"


class BDCTransferResponseWrapper(BaseModel):
    """Wrapper de respuesta de transferencia"""
    statusCode: Optional[int] = None
    data: Optional[BDCTransferResponseData] = None
    time: Optional[str] = None
    
    class Config:
        extra = "allow"  # Permite campos adicionales


class BDCTransferDetailData(BaseModel):
    """Datos completos de una transferencia"""
    request: Optional[BDCTransferRequestData] = Field(None, description="Datos del request original")
    response: Optional[BDCTransferResponseData] = Field(None, description="Respuesta de BDC")
    error: Optional[Dict] = Field(None, description="Información de error si existe")
    estado: Optional[str] = Field(None, description="Estado de la transferencia: PENDING, COMPLETED, FAILED, etc.")
    
    class Config:
        extra = "allow"  # Permite campos adicionales que BDC pueda enviar


class BDCTransferDetailResponse(BaseModel):
    """Schema para respuesta detallada de consulta de transferencia"""
    statusCode: int = Field(..., description="Código de estado (0=éxito, otros=error)")
    data: Optional[BDCTransferDetailData] = Field(None, description="Detalles de la transferencia (solo si statusCode=0)")
    message: Optional[str] = Field(None, description="Mensaje de error (cuando statusCode != 0)")
    time: str = Field(..., description="Timestamp del servidor BDC")


class BDCTransferDetailSimpleResponse(BaseModel):
    """Schema para respuesta simplificada de consulta de transferencia"""
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    data: BDCTransferResponseData = Field(..., description="Datos de respuesta del banco")
    time: str = Field(..., description="Timestamp del servidor BDC")
    estado: str = Field(..., description="Estado de la transferencia: PENDING, COMPLETED, FAILED, etc.")


# ============= Actualización de Cuentas/Alias =============

class BDCUpdateAccountLabelRequest(BaseModel):
    """Schema para request de actualización de alias de cuenta"""
    accountLabel: str = Field(..., description="Nuevo alias para la cuenta (formato: palabra.palabra.palabra)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "accountLabel": "alias.example"
            }
        }


class BDCUpdateSubAccountRequest(BaseModel):
    """Schema para request de edición de subcuenta (alias/estado)"""
    status: Optional[str] = Field(None, description="Estado de la subcuenta: ACTIVE/SUSPENDED/etc.")
    accountLabel: Optional[str] = Field(None, description="Nuevo alias para la cuenta (formato: palabra.palabra.palabra)")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ACTIVE"
            }
        }


class BDCAccountData(BaseModel):
    """Datos de cuenta actualizados"""
    accountId: str = Field(..., description="ID de la cuenta")
    status: str = Field(..., description="Estado de la cuenta: active, suspended, etc.")
    accountLabel: str = Field(..., description="Alias de la cuenta")
    updatedAt: str = Field(..., description="Fecha y hora de actualización")


class BDCUpdateAccountResponse(BaseModel):
    """Schema para respuesta de actualización de cuenta"""
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    message: str = Field(..., description="Mensaje descriptivo")
    data: BDCAccountData = Field(..., description="Datos de la cuenta actualizada")
    time: Optional[str] = Field(None, description="Timestamp del servidor BDC (opcional)")


# ============= Movimientos =============

class BDCMovementsRequest(BaseModel):
    """Schema para request de listado de movimientos"""
    startDate: str = Field(..., description="Fecha desde (YYYY-MM-DD)")
    endDate: str = Field(..., description="Fecha hasta (YYYY-MM-DD)")
    pageSize: int = Field(..., gt=0, description="Tamaño de página (debe ser mayor a 0)")
    pageOffset: int = Field(..., gt=0, description="Offset de página (debe ser mayor a 0)")


class BDCMovimientoDatoAdicional(BaseModel):
    """Datos adicionales de movimiento"""
    idCoelsa: str
    cuitOrigen: str
    cbuOrigen: str
    cuitDestino: str
    cbuDestino: str
    titular: str


class BDCMovimientoDatosAdicionales(BaseModel):
    """Wrapper de datos adicionales"""
    sBTDatoAdicional: BDCMovimientoDatoAdicional


class BDCMovimiento(BaseModel):
    """Movimiento de cuenta"""
    movimientoUId: str
    fechaMov: str
    fechaSis: str
    horaSis: str
    concepto: str
    referencia: str
    numeroCheque: str
    debitoCredito: str
    moneda: str
    importe: float
    saldo: float
    datosAdicionales: BDCMovimientoDatosAdicionales


class BDCMovimientos(BaseModel):
    """Listado de movimientos"""
    SdtsBTMovimiento: list[BDCMovimiento]
    class Config:
        extra = "allow"


class BDCEstadoDeCuenta(BaseModel):
    """Estado de cuenta"""
    productoUID: str
    fechaDesde: str
    fechaHasta: str
    saldoPartida: float
    totalRegistros: int
    movimientos: BDCMovimientos
    class Config:
        extra = "allow"


class BDCMovementsData(BaseModel):
    """Datos de respuesta de movimientos"""
    sdtEstadoDeCuenta: BDCEstadoDeCuenta
    class Config:
        extra = "allow"


class BDCMovementsResponse(BaseModel):
    """Schema para respuesta de movimientos"""
    statusCode: int
    message: Optional[str] = None
    time: Optional[str] = None
    data: Optional[BDCMovementsData] = None
    class Config:
        extra = "allow"


class BDCUltimosMovimientosRequest(BaseModel):
    """Schema para request a apiV1/ultimosMovimientos"""
    cbu: str = Field(default="", description="CBU de la cuenta origen")
    cvu: str = Field(default="", description="CVU de la cuenta origen")
    startDate: str = Field(..., description="Fecha desde (YYYY-MM-DD)")
    endDate: str = Field(..., description="Fecha hasta (YYYY-MM-DD)")
    pageSize: int = Field(..., gt=0, description="Página (base 1)")
    pageOffset: int = Field(..., gt=0, description="Cantidad de movimientos por página")


# ============= Cuentas =============

class BDCAccountRouting(BaseModel):
    """Direcciones de cuenta (CBU, etc.)"""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    addresstype: str = Field(
        ...,
        alias="addressType",
        description="Tipo de dirección: CBU, CVU, etc.",
    )
    address: str = Field(..., description="Dirección bancaria")


class BDCAccountOwner(BaseModel):
    """Propietario de la cuenta"""
    model_config = ConfigDict(extra="allow")

    personId: Optional[str] = Field(None, description="ID de la persona")
    personIdType: Optional[str] = Field(None, description="Tipo de identificación")
    personName: Optional[str] = Field(None, description="Nombre de la persona")
    personType: Optional[str] = Field(None, description="Tipo de persona: LEGAL/FISICA")


class BDCAccountBalance(BaseModel):
    """Balance de cuenta"""
    model_config = ConfigDict(extra="allow")

    balanceCurrency: Optional[str] = Field(None, description="Código de moneda")
    balanceConcept: Optional[str] = Field(None, description="Concepto del balance")
    balanceAmount: Optional[float] = Field(None, description="Monto del balance")
    balanceWithheldAmount: Optional[float] = Field(None, description="Monto retenido")


class BDCAccountInfo(BaseModel):
    """Información adicional de la cuenta"""
    model_config = ConfigDict(extra="allow")

    status: Optional[str] = Field(None, description="Estado de la cuenta")
    networks: list[str] = Field(default_factory=list, description="Redes")
    currencies: list[str] = Field(default_factory=list, description="Monedas")
    taxes: list[str] = Field(default_factory=list, description="Impuestos")
    apiOperable: Optional[bool] = Field(None, description="Si la cuenta es operable por API")
    parentAccount: Optional[bool] = Field(None, description="Si es cuenta padre")


class BDCAccount(BaseModel):
    """Cuenta bancaria BDC"""
    model_config = ConfigDict(extra="allow")

    accountId: str = Field(..., description="ID de la cuenta")
    accountType: Optional[str] = Field(None, description="Tipo de cuenta")
    accountLabel: Optional[str] = Field(None, description="Alias de la cuenta")
    accountNumber: Optional[str] = Field(None, description="Número de cuenta")
    accountRouting: list[BDCAccountRouting] = Field(default_factory=list, description="Ruteos de cuenta")
    owners: list[BDCAccountOwner] = Field(default_factory=list, description="Propietarios")
    balances: list[BDCAccountBalance] = Field(default_factory=list, description="Balances")
    info: Optional[BDCAccountInfo] = Field(None, description="Información adicional")


class BDCAccountsData(BaseModel):
    """Datos de cuentas de BDC"""
    model_config = ConfigDict(extra="allow")

    entityType: Optional[str] = Field(None, description="Tipo de entidad")
    entityCode: Optional[str] = Field(None, description="Código de entidad")
    entityName: Optional[str] = Field(None, description="Nombre de entidad")
    accounts: list[BDCAccount] = Field(default_factory=list, description="Listado de cuentas")


class BDCAccountsResponse(BaseModel):
    """Schema para respuesta de cuentas BDC"""
    model_config = ConfigDict(extra="allow")

    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    data: Optional[BDCAccountsData] = Field(None, description="Datos de cuentas")
    time: Optional[str] = Field(None, description="Timestamp del servidor BDC")


# ============= Información de Cuenta =============

class BDCAccountInfoOwner(BaseModel):
    """Propietario de la cuenta (info)"""
    id: str = Field(..., description="Identificador del propietario")
    displayName: str = Field(..., description="Nombre del propietario")
    idType: str = Field(..., description="Tipo de identificación")
    isPhysicalPerson: bool = Field(..., description="Indica si es persona física")


class BDCAccountInfoRouting(BaseModel):
    """Ruteo de cuenta (info)"""
    scheme: str = Field(..., description="Esquema de ruteo: CBU, CVU, etc.")
    address: str = Field(..., description="Dirección bancaria")


class BDCAccountInfoEntityRouting(BaseModel):
    """Entidad bancaria (info)"""
    type: str = Field(..., description="Tipo de entidad")
    name: str = Field(..., description="Nombre de la entidad")
    code: str = Field(..., description="Código de la entidad")


class BDCAccountInfoData(BaseModel):
    """Datos de información de cuenta BDC"""
    owners: list[BDCAccountInfoOwner] = Field(..., description="Propietarios")
    type: str = Field(..., description="Tipo de cuenta")
    isActive: bool = Field(..., description="Indica si la cuenta está activa")
    currency: str = Field(..., description="Código de moneda")
    label: str = Field(..., description="Alias de la cuenta")
    accountRouting: BDCAccountInfoRouting = Field(..., description="Ruteo de cuenta")
    entityRouting: BDCAccountInfoEntityRouting = Field(..., description="Entidad bancaria")


class BDCAccountInfoResponse(BaseModel):
    """Schema para respuesta de info de cuenta BDC"""
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    data: BDCAccountInfoData = Field(..., description="Datos de la cuenta")
    time: str = Field(..., description="Timestamp del servidor BDC")


# ============= Listado de Subcuentas (CVU) =============

class BDCGetCvuAccountsRequest(BaseModel):
    """Schema para request de listado de subcuentas CVU"""
    cbu: str = Field(..., description="CBU de la cuenta")
    pageOffset: int = Field(..., description="Offset de página")
    pageSize: int = Field(..., description="Tamaño de página")
    sortDirection: str = Field(..., description="Dirección de orden: ASC/DESC")


# ============= Creación de Subcuentas =============

class BDCSubAccountOwner(BaseModel):
    """Propietario de la subcuenta"""
    personIdType: str = Field(..., description="Tipo de identificación")
    personId: str = Field(..., description="Número de identificación")
    personName: str = Field(..., description="Nombre del propietario")


class BDCSubAccountCreateRequest(BaseModel):
    """Schema para request de creación de subcuenta"""
    # Token se recibe como query parameter, no en el body
    pass  # No se requieren datos en el body, solo el token JWT


# ============= Response de Creación de Subcuenta =============

class BDCSubAccountCreateResponseRouting(BaseModel):
    """Routing address de la subcuenta creada"""
    addressType: str = Field(..., description="Tipo de dirección: CBU, CVU, etc.")
    address: str = Field(..., description="Dirección (CBU/CVU)")


class BDCSubAccountCreateResponseOwner(BaseModel):
    """Propietario en la respuesta de creación de subcuenta"""
    personId: str = Field(..., description="Identificación del propietario")
    personIdType: str = Field(..., description="Tipo de identificación: CUI, CUIL, DNI, etc.")
    personName: str = Field(..., description="Nombre del propietario")
    personType: str = Field(..., description="Tipo de persona: OWNER, LEGAL, etc.")


class BDCSubAccountCreateResponseInfo(BaseModel):
    """Información adicional de la subcuenta"""
    status: str = Field(..., description="Estado de la cuenta: ACTIVE, INACTIVE, etc.")
    currencies: list[str] = Field(..., description="Monedas soportadas (ej: 032=ARS)")


class BDCSubAccountCreateResponseEntityRouting(BaseModel):
    """Información de la entidad bancaria"""
    entityType: str = Field(..., description="Tipo de entidad: BANK")
    entityCode: str = Field(..., description="Código de la entidad")
    entityName: str = Field(..., description="Nombre de la entidad")


class BDCSubAccountCreateResponseData(BaseModel):
    """Datos de respuesta de creación de subcuenta"""
    accountId: str = Field(..., description="ID único de la cuenta creada")
    accountType: str = Field(..., description="Tipo de cuenta: CHECKING_ACCOUNT, etc.")
    accountLabel: str = Field(..., description="Alias/etiqueta de la cuenta")
    accountRouting: list[BDCSubAccountCreateResponseRouting] = Field(..., description="Información de routing")
    owners: list[BDCSubAccountCreateResponseOwner] = Field(..., description="Propietarios de la cuenta")
    entityRouting: BDCSubAccountCreateResponseEntityRouting = Field(..., description="Información de la entidad")
    info: BDCSubAccountCreateResponseInfo = Field(..., description="Información adicional")


class BDCSubAccountCreateSimpleResponse(BaseModel):
    """Schema simplificado para respuesta de creación de subcuenta"""
    accountId: str = Field(..., description="ID único de la cuenta creada")
    accountType: str = Field(..., description="Tipo de cuenta: CHECKING_ACCOUNT, etc.")
    accountLabel: str = Field(..., description="Alias/etiqueta de la cuenta")


class BDCSubAccountCreateAppResponse(BaseModel):
    """Respuesta simplificada para la APP"""
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    data: BDCSubAccountCreateSimpleResponse = Field(..., description="Datos básicos de la subcuenta")


class BDCSubAccountCreateResponse(BaseModel):
    """Schema completo para respuesta de creación de subcuenta"""
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    data: BDCSubAccountCreateResponseData = Field(..., description="Datos de la subcuenta creada")
    time: str = Field(..., description="Timestamp del servidor")


# ============= Consulta de Subcuentas =============

class BDCSubAccountAliasMessage(BaseModel):
    """Mensaje de alias en respuesta CVU"""
    valor: str


class BDCSubAccountRespuesta(BaseModel):
    """Respuesta genérica"""
    codigo: str
    descripcion: str


class BDCSubAccountCvuMensaje(BaseModel):
    """Mensaje de respuesta CVU"""
    alias: BDCSubAccountAliasMessage
    respuesta: BDCSubAccountRespuesta


class BDCSubAccountResponseCvu(BaseModel):
    """Respuesta CVU Coelsa"""
    statusCode: int
    mensaje: BDCSubAccountCvuMensaje


class BDCSubAccountTitular(BaseModel):
    """Titular de la cuenta"""
    tipo_persona: str
    cuit: str
    nombre: str


class BDCSubAccountCuenta(BaseModel):
    """Datos de cuenta en respuesta Alias"""
    tipo_cta: str
    nro_cbu_anterior: Optional[str] = None
    nro_bco: str
    cta_activa: bool
    nro_cbu: str


class BDCSubAccountAliasRespuesta(BaseModel):
    """Respuesta en Alias Coelsa"""
    numero: str
    descripcion: str


class BDCSubAccountAliasInfo(BaseModel):
    """Alias en respuesta Alias Coelsa"""
    valor: str
    valor_original: Optional[str] = None
    id: Optional[str] = None


class BDCSubAccountAliasMensaje(BaseModel):
    """Mensaje de respuesta Alias Coelsa"""
    titular: BDCSubAccountTitular
    cuenta: BDCSubAccountCuenta
    respuesta: BDCSubAccountAliasRespuesta
    alias: BDCSubAccountAliasInfo
    titulares: list = Field(default_factory=list)
    transac: str
    reasigna: Optional[str] = None


class BDCSubAccountResponseAlias(BaseModel):
    """Respuesta Alias Coelsa"""
    statusCode: int
    mensaje: BDCSubAccountAliasMensaje


class BDCSubAccountQueryData(BaseModel):
    """Datos de respuesta de consulta de subcuenta"""
    model_config = ConfigDict(extra="allow")

    responseCvuCoelsa: Optional[BDCSubAccountResponseCvu] = None
    responseAliasCoelsa: Optional[BDCSubAccountResponseAlias] = None


class BDCSubAccountQueryResponse(BaseModel):
    """Schema para respuesta de consulta de subcuenta"""
    statusCode: int
    data: BDCSubAccountQueryData | BDCSubAccountCreateResponseData | Dict[str, Any]
    time: Optional[str] = None


# ============= Token Cache =============

class BDCTokenCache(BaseModel):
    """Schema para almacenar token en cache"""
    access_token: str
    expires_at: datetime
    created_at: datetime

    def is_expired(self) -> bool:
        """Verifica si el token está expirado"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) >= self.expires_at
    
    def is_expiring_soon(self, buffer_seconds: int = 60) -> bool:
        """Verifica si el token está por expirar (con buffer)"""
        from datetime import datetime, timezone, timedelta
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(seconds=buffer_seconds))


# ============= Healthcheck =============

class BDCHealthcheckResponse(BaseModel):
    """Schema para respuesta de healthcheck de BDC - Permite campos extra del banco"""
    model_config = ConfigDict(extra="allow")
    
    statusCode: int = Field(..., description="Código de estado (0=ok)")
    time: Optional[str] = Field(None, description="Timestamp del servidor BDC")


# ============= SNP Concepts =============

class BDCSnpConcept(BaseModel):
    """Schema para un concepto SNP individual"""
    id: str = Field(..., description="ID del concepto")
    description: str = Field(..., description="Descripción del concepto")


class BDCSnpConceptsData(BaseModel):
    """Schema para datos de conceptos SNP"""
    concepts: list[BDCSnpConcept] = Field(default_factory=list, description="Lista de conceptos disponibles")


class BDCSnpConceptsResponse(BaseModel):
    """Schema para respuesta de conceptos SNP de transferencias"""
    statusCode: int = Field(..., description="Código de estado (0=éxito)")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos de conceptos")
    time: Optional[str] = Field(None, description="Timestamp del servidor BDC")


# ============= Error Handling =============

class BDCErrorResponse(BaseModel):
    """Schema para errores de BDC"""
    statusCode: int
    message: str
    detail: Optional[str] = None
