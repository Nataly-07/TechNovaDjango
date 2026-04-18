import uuid
from datetime import datetime

from collections import OrderedDict

from django.db.models import Q
from django.utils import timezone

from atencion_cliente.models import Reclamo
from mensajeria.domain.repositories import MensajeriaQueryPort
from mensajeria.models import MensajeDirecto, MensajeEmpleado, Notificacion
from usuario.models import Usuario
from venta.models import Venta


class MensajeriaQueryRepository(MensajeriaQueryPort):
    def _notif_dict(self, n: Notificacion) -> dict:
        extra = n.data_adicional if isinstance(n.data_adicional, dict) else {}
        return {
            "id": n.id,
            "userId": n.usuario_id,
            "usuario_id": n.usuario_id,
            "titulo": n.titulo,
            "mensaje": n.mensaje,
            "tipo": n.tipo,
            "icono": n.icono or "bell",
            "leida": n.leida,
            "fechaCreacion": n.fecha_creacion.isoformat(),
            "data_adicional": extra,
        }

    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        queryset = Notificacion.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [self._notif_dict(n) for n in queryset]

    def listar_notificaciones_todas(self) -> list[dict]:
        return [self._notif_dict(n) for n in Notificacion.objects.order_by("-id")]

    def listar_notificaciones_filtradas(
        self,
        usuario_id: int,
        *,
        solo_no_leidas: bool = False,
        leida: bool | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[dict]:
        queryset = Notificacion.objects.filter(usuario_id=usuario_id).order_by("-id")
        if solo_no_leidas:
            queryset = queryset.filter(leida=False)
        if leida is not None:
            queryset = queryset.filter(leida=leida)
        if desde is not None:
            queryset = queryset.filter(fecha_creacion__gte=desde)
        if hasta is not None:
            queryset = queryset.filter(fecha_creacion__lte=hasta)
        return [self._notif_dict(n) for n in queryset]

    def marcar_notificacion_leida(self, usuario_id: int, notificacion_id: int) -> bool:
        updated = Notificacion.objects.filter(pk=notificacion_id, usuario_id=usuario_id).update(
            leida=True
        )
        return updated > 0

    def marcar_todas_notificaciones_leidas(self, usuario_id: int) -> int:
        return Notificacion.objects.filter(usuario_id=usuario_id, leida=False).update(leida=True)

    def _md_dict(self, m: MensajeDirecto) -> dict:
        return {
            "id": m.id,
            "conversationId": m.conversacion_id,
            "senderId": m.remitente_usuario_id,
            "senderType": m.tipo_remitente,
            "receiverId": m.destinatario_usuario_id,
            "subject": m.asunto,
            "message": m.mensaje,
            "priority": m.prioridad,
            "state": m.estado,
            "isRead": m.leido,
            "createdAt": m.creado_en.isoformat(),
            "parentMessageId": m.mensaje_padre_id,
        }

    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        queryset = MensajeDirecto.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(
                Q(destinatario_usuario_id=usuario_id) | Q(remitente_usuario_id=usuario_id)
            )
        return [self._md_dict(m) for m in queryset]

    def listar_mensajes_directos_todos(self) -> list[dict]:
        return [self._md_dict(m) for m in MensajeDirecto.objects.order_by("-id")]

    def listar_mensajes_por_empleado(self, empleado_id: int) -> list[dict]:
        queryset = MensajeDirecto.objects.filter(
            Q(empleado_asignado_id=empleado_id) | Q(destinatario_usuario_id=empleado_id)
        ).order_by("-id")
        return [self._md_dict(m) for m in queryset]

    def listar_mensajes_por_conversacion(self, conversacion_id: str) -> list[dict]:
        return [
            self._md_dict(m)
            for m in MensajeDirecto.objects.filter(conversacion_id=conversacion_id).order_by(
                "creado_en", "id"
            )
        ]

    def obtener_mensaje_directo(self, mensaje_id: int) -> dict | None:
        m = MensajeDirecto.objects.filter(id=mensaje_id).first()
        return self._md_dict(m) if m else None

    def crear_mensaje_directo(self, data: dict) -> int:
        payload = {**data}
        if payload.get("mensaje_padre_id") is None:
            payload.pop("mensaje_padre_id", None)
        mensaje = MensajeDirecto.objects.create(**payload)
        return mensaje.id

    def crear_conversacion_inicial(
        self, usuario_id: int, asunto: str, mensaje: str, prioridad: str
    ) -> dict:
        prioridad_n = (prioridad or "normal").lower()
        if prioridad_n not in {c[0] for c in MensajeDirecto.Prioridad.choices}:
            prioridad_n = MensajeDirecto.Prioridad.NORMAL
        conv = str(uuid.uuid4())
        m = MensajeDirecto.objects.create(
            conversacion_id=conv,
            mensaje_padre=None,
            tipo_remitente=MensajeDirecto.TipoRemitente.CLIENTE,
            remitente_usuario_id=usuario_id,
            destinatario_usuario_id=None,
            asunto=asunto.strip(),
            mensaje=mensaje.strip(),
            prioridad=prioridad_n,
            estado=MensajeDirecto.Estado.ENVIADO,
            leido=False,
        )
        return self._md_dict(m)

    def responder_mensaje_directo(
        self, mensaje_padre_id: int, sender_id: int, sender_type: str, texto: str
    ) -> dict | None:
        padre = MensajeDirecto.objects.filter(id=mensaje_padre_id).first()
        if padre is None:
            return None
        st = sender_type.strip().lower()
        if st == "employee":
            st = "empleado"
        if st == "client":
            st = "cliente"
        if st not in (MensajeDirecto.TipoRemitente.CLIENTE, MensajeDirecto.TipoRemitente.EMPLEADO):
            raise ValueError("senderType debe ser cliente o empleado.")

        if st == MensajeDirecto.TipoRemitente.EMPLEADO:
            dest_id = padre.remitente_usuario_id
        else:
            dest_id = padre.destinatario_usuario_id or padre.empleado_asignado_id

        hijo = MensajeDirecto.objects.create(
            conversacion_id=padre.conversacion_id,
            mensaje_padre=padre,
            tipo_remitente=st,
            remitente_usuario_id=sender_id,
            destinatario_usuario_id=dest_id,
            asunto=padre.asunto,
            mensaje=texto.strip(),
            prioridad=padre.prioridad,
            estado=MensajeDirecto.Estado.ENVIADO,
            empleado_asignado_id=padre.empleado_asignado_id,
            leido=False,
        )
        padre.estado = MensajeDirecto.Estado.RESPONDIDO
        padre.save(update_fields=["estado", "actualizado_en"])
        return self._md_dict(hijo)

    def marcar_mensaje_leido(self, mensaje_id: int) -> dict | None:
        m = MensajeDirecto.objects.filter(id=mensaje_id).first()
        if m is None:
            return None
        m.leido = True
        m.leido_en = timezone.now()
        m.estado = MensajeDirecto.Estado.LEIDO
        m.save(update_fields=["leido", "leido_en", "estado", "actualizado_en"])
        return self._md_dict(m)

    def estadisticas_mensajes_directos(self) -> dict:
        todos = list(MensajeDirecto.objects.order_by("-creado_en"))
        por_conv: dict[str, MensajeDirecto] = {}
        for m in todos:
            if not m.conversacion_id:
                continue
            prev = por_conv.get(m.conversacion_id)
            if prev is None or m.creado_en > prev.creado_en:
                por_conv[m.conversacion_id] = m
        no_leidos = 0
        for ult in por_conv.values():
            es_leido = (
                ult.leido
                or ult.estado == MensajeDirecto.Estado.RESPONDIDO
                or ult.tipo_remitente == MensajeDirecto.TipoRemitente.EMPLEADO
            )
            if not es_leido:
                no_leidos += 1
        return {"mensajes": len(por_conv), "noLeidos": no_leidos}

    def listar_mensajes_empleado(self, empleado_id: int | None) -> list[dict]:
        queryset = MensajeEmpleado.objects.order_by("-id")
        if empleado_id:
            queryset = queryset.filter(empleado_usuario_id=empleado_id)
        return [
            {
                "id": m.id,
                "empleado_usuario_id": m.empleado_usuario_id,
                "remitente_usuario_id": m.remitente_usuario_id,
                "asunto": m.asunto,
                "tipo": m.tipo,
                "prioridad": m.prioridad,
                "leido": m.leido,
            }
            for m in queryset
        ]

    def crear_mensaje_empleado(self, data: dict) -> int:
        mensaje = MensajeEmpleado.objects.create(**data)
        return mensaje.id

    def _staff_chat_dict(self, m: MensajeEmpleado) -> dict:
        rem = m.remitente_usuario
        rem_nombre = f"{rem.nombres or ''} {rem.apellidos or ''}".strip() if rem else ""
        return {
            "id": m.id,
            "empleadoUsuarioId": m.empleado_usuario_id,
            "remitenteUsuarioId": m.remitente_usuario_id,
            "tipoRemitente": m.tipo_remitente,
            "remitenteNombre": rem_nombre,
            "asunto": m.asunto,
            "mensaje": m.mensaje,
            "tipo": m.tipo,
            "prioridad": m.prioridad,
            "leido": m.leido,
            "fechaLeido": m.fecha_leido.isoformat() if m.fecha_leido else None,
            "reclamoId": m.reclamo_id,
            "creadoEn": m.creado_en.isoformat(),
            "dataAdicional": m.data_adicional or {},
        }

    def historial_staff_chat(self, empleado_thread_id: int) -> list[dict]:
        qs = (
            MensajeEmpleado.objects.select_related("remitente_usuario", "empleado_usuario")
            .filter(empleado_usuario_id=empleado_thread_id)
            .order_by("creado_en", "id")
        )
        return [self._staff_chat_dict(m) for m in qs]

    def resumen_conversaciones_staff_admin(self) -> list[dict]:
        emp_ids = list(
            MensajeEmpleado.objects.values_list("empleado_usuario_id", flat=True).distinct()
        )
        resumen: list[dict] = []
        for eid in emp_ids:
            last = (
                MensajeEmpleado.objects.filter(empleado_usuario_id=eid)
                .select_related("remitente_usuario", "empleado_usuario")
                .order_by("-creado_en", "-id")
                .first()
            )
            if last is None:
                continue
            unread = MensajeEmpleado.objects.filter(
                empleado_usuario_id=eid,
                tipo_remitente=MensajeEmpleado.TipoRemitente.EMPLEADO,
                leido=False,
            ).count()
            emp = Usuario.objects.filter(pk=eid).first()
            nombre = ""
            if emp:
                nombre = f"{emp.nombres or ''} {emp.apellidos or ''}".strip()
            resumen.append(
                {
                    "empleadoUsuarioId": eid,
                    "empleadoNombre": nombre or f"Empleado #{eid}",
                    "empleadoCorreo": getattr(emp, "correo_electronico", "") or "",
                    "ultimoMensaje": (last.mensaje or "")[:160],
                    "ultimoAsunto": last.asunto,
                    "ultimoCreadoEn": last.creado_en.isoformat(),
                    "noLeidosAdmin": unread,
                }
            )
        resumen.sort(key=lambda x: x["ultimoCreadoEn"], reverse=True)
        return resumen

    def buscar_empleados_staff_chat(self, query: str, *, limit: int) -> list[dict]:
        q = (query or "").strip()
        lim = max(1, min(limit, 80))
        qs = Usuario.objects.filter(rol=Usuario.Rol.EMPLEADO, activo=True).order_by("id")
        if q:
            qs = qs.filter(
                Q(nombres__icontains=q)
                | Q(apellidos__icontains=q)
                | Q(correo_electronico__icontains=q)
                | Q(numero_documento__icontains=q)
            )
        return [
            {
                "id": u.id,
                "nombre": f"{u.nombres or ''} {u.apellidos or ''}".strip(),
                "correo": u.correo_electronico or "",
            }
            for u in qs[:lim]
        ]

    def crear_mensaje_staff_chat(
        self,
        *,
        empleado_usuario_id: int,
        remitente_usuario_id: int,
        tipo_remitente: str,
        asunto: str,
        mensaje: str,
        tipo_mensaje: str,
        reclamo_id: int | None,
        prioridad: str,
    ) -> dict | None:
        emp = Usuario.objects.filter(pk=empleado_usuario_id, rol=Usuario.Rol.EMPLEADO).first()
        if emp is None:
            return None
        rem = Usuario.objects.filter(pk=remitente_usuario_id).first()
        if rem is None:
            return None
        tr = (tipo_remitente or "").strip().lower()
        valid_tr = {c[0] for c in MensajeEmpleado.TipoRemitente.choices}
        if tr not in valid_tr:
            return None
        if tr == MensajeEmpleado.TipoRemitente.EMPLEADO:
            if remitente_usuario_id != empleado_usuario_id or rem.rol != Usuario.Rol.EMPLEADO:
                return None
        elif tr in (
            MensajeEmpleado.TipoRemitente.ADMIN,
            MensajeEmpleado.TipoRemitente.SISTEMA,
        ):
            if rem.rol != Usuario.Rol.ADMIN:
                return None
        else:
            return None
        pr = (prioridad or "normal").strip().lower()
        if pr not in {c[0] for c in MensajeEmpleado.Prioridad.choices}:
            pr = MensajeEmpleado.Prioridad.NORMAL
        reclamo = None
        if reclamo_id is not None:
            reclamo = Reclamo.objects.filter(id=reclamo_id).first()
            if reclamo is None:
                return None
        extra: dict = {}
        if reclamo_id is not None:
            extra["reclamoId"] = reclamo_id
            extra["ticketUrl"] = f"/empleado/reclamos/"
        m = MensajeEmpleado.objects.create(
            empleado_usuario_id=empleado_usuario_id,
            remitente_usuario_id=remitente_usuario_id,
            tipo_remitente=tr,
            asunto=(asunto or "").strip()[:200] or "Mensaje",
            mensaje=(mensaje or "").strip(),
            tipo=(tipo_mensaje or "general").strip()[:50] or "general",
            prioridad=pr,
            leido=False,
            reclamo=reclamo,
            data_adicional=extra,
        )
        m = MensajeEmpleado.objects.select_related("remitente_usuario", "empleado_usuario").get(
            pk=m.id
        )
        return self._staff_chat_dict(m)

    def marcar_staff_chat_leido(self, empleado_thread_id: int, lector_id: int, lector_rol: str) -> int:
        rol = (lector_rol or "").strip().lower()
        now = timezone.now()
        if rol == "admin":
            return MensajeEmpleado.objects.filter(
                empleado_usuario_id=empleado_thread_id,
                tipo_remitente=MensajeEmpleado.TipoRemitente.EMPLEADO,
                leido=False,
            ).update(leido=True, fecha_leido=now)
        if rol == "empleado":
            return (
                MensajeEmpleado.objects.filter(
                    empleado_usuario_id=empleado_thread_id,
                    leido=False,
                )
                .exclude(remitente_usuario_id=lector_id)
                .update(leido=True, fecha_leido=now)
            )
        return 0

    def detalle_reclamo_staff_chat(self, reclamo_id: int) -> dict | None:
        r = Reclamo.objects.select_related("usuario", "empleado_asignado").filter(id=reclamo_id).first()
        if r is None:
            return None
        cli = r.usuario
        cli_nombre = f"{cli.nombres or ''} {cli.apellidos or ''}".strip() if cli else ""
        compras = Venta.objects.filter(usuario_id=r.usuario_id).order_by("-fecha_venta", "-id")[:8]
        compras_list = [
            {
                "id": v.id,
                "fecha": v.fecha_venta.isoformat(),
                "total": str(v.total),
                "estado": v.estado,
            }
            for v in compras
        ]
        return {
            "id": r.id,
            "titulo": r.titulo,
            "descripcion": r.descripcion,
            "estado": r.estado,
            "prioridad": r.prioridad,
            "respuesta": r.respuesta or "",
            "clienteNombre": cli_nombre,
            "clienteCorreo": getattr(cli, "correo_electronico", "") or "",
            "fechaReclamo": r.fecha_reclamo.isoformat(),
            "empleadoAsignadoId": r.empleado_asignado_id,
            "comprasRecientes": compras_list,
        }

    # -------------------- SSR contexts (hexagonal estricto) --------------------
    def _mensaje_empleado_dto(self, m: MensajeEmpleado) -> dict:
        return {
            "id": m.id,
            "empleadoId": m.empleado_usuario_id,
            "remitenteId": m.remitente_usuario_id,
            "tipoRemitente": m.tipo_remitente,
            "asunto": m.asunto,
            "mensaje": m.mensaje,
            "tipo": m.tipo,
            "prioridad": m.prioridad,
            "leido": m.leido,
            "createdAt": m.creado_en,
        }

    def _nombre_usuario(self, u: Usuario | None) -> str:
        if not u:
            return ""
        return f"{u.nombres or ''} {u.apellidos or ''}".strip()

    def _reclamos_enviados_al_admin_ssr(self) -> list[dict]:
        qs = (
            Reclamo.objects.filter(enviado_al_admin=True)
            .select_related("usuario", "empleado_asignado")
            .order_by("-fecha_reclamo", "-id")
        )
        return [
            {
                "id": r.id,
                "titulo": r.titulo,
                "descripcion": r.descripcion,
                "estado": r.estado,
                "prioridad": r.prioridad,
                "fechaReclamo": r.fecha_reclamo,
                "respuesta": r.respuesta or "",
                "evaluacionCliente": (r.evaluacion_cliente or "").strip(),
            }
            for r in qs
        ]

    def admin_mensajes_ssr_context(
        self,
        *,
        conversacion_id: int | None,
        marcar_leidos: bool,
        admin_usuario_id: int,
    ) -> dict:
        if conversacion_id is not None and marcar_leidos:
            self.marcar_staff_chat_leido(conversacion_id, admin_usuario_id, "admin")

        todos = list(
            MensajeEmpleado.objects.select_related("remitente_usuario", "empleado_usuario").order_by(
                "-creado_en", "-id"
            )
        )

        conversaciones_temp: dict[int, list[MensajeEmpleado]] = {}
        for m in todos:
            conversaciones_temp.setdefault(m.empleado_usuario_id, []).append(m)
        for _, msgs in conversaciones_temp.items():
            msgs.sort(key=lambda x: (x.creado_en, x.id), reverse=True)

        no_leidos_por_conversacion: dict[int, int] = {}
        for eid, msgs in conversaciones_temp.items():
            no_leidos_por_conversacion[eid] = sum(1 for x in msgs if not x.leido)

        ordenadas = sorted(
            conversaciones_temp.items(),
            key=lambda kv: kv[1][0].creado_en if kv[1] else timezone.now(),
            reverse=True,
        )
        conversaciones: OrderedDict[int, list[MensajeEmpleado]] = OrderedDict(ordenadas)

        empleados = list(
            Usuario.objects.filter(rol=Usuario.Rol.EMPLEADO, activo=True).order_by("nombres", "id")[:800]
        )
        nombres_empleados: dict[int, str] = {}
        for emp in empleados:
            nombres_empleados[emp.id] = self._nombre_usuario(emp) or f"Empleado #{emp.id}"

        conversaciones_list: list[dict] = []
        for emp_id, msgs in conversaciones.items():
            nombre = nombres_empleados.get(emp_id) or f"Empleado #{emp_id}"
            inicial = (nombre.strip()[:1] or "E").upper()
            conversaciones_list.append(
                {
                    "empleado_id": emp_id,
                    "lista": msgs,
                    "nombre": nombre,
                    "inicial": inicial,
                    "no_leidos": no_leidos_por_conversacion.get(emp_id, 0),
                }
            )

        mensajes_conversacion: list[dict] = []
        empleado_conversacion: Usuario | None = None
        if conversacion_id is not None:
            mensajes_conversacion = [
                self._mensaje_empleado_dto(m) for m in todos if m.empleado_usuario_id == conversacion_id
            ]
            empleado_conversacion = Usuario.objects.filter(pk=conversacion_id).first()

        return {
            "conversaciones_list": conversaciones_list,
            "conversacion_id": conversacion_id,
            "mensajes_conversacion": mensajes_conversacion,
            "empleado_conversacion": empleado_conversacion,
            "empleados": empleados,
            "reclamos_empleados": self._reclamos_enviados_al_admin_ssr(),
        }

    def empleado_mensajes_ssr_context(
        self,
        *,
        empleado_id: int,
        conversacion_admin_id: int | None,
        marcar_leidos: bool,
    ) -> dict:
        if conversacion_admin_id is not None and marcar_leidos:
            self.marcar_staff_chat_leido(empleado_id, empleado_id, "empleado")

        todos = list(
            MensajeEmpleado.objects.filter(empleado_usuario_id=empleado_id)
            .select_related("remitente_usuario", "empleado_usuario")
            .order_by("-creado_en", "-id")
        )

        conversaciones_temp: dict[int, list[MensajeEmpleado]] = {}
        for m in todos:
            if m.tipo_remitente == MensajeEmpleado.TipoRemitente.ADMIN and m.remitente_usuario_id:
                conversaciones_temp.setdefault(m.remitente_usuario_id, []).append(m)
        for _, msgs in conversaciones_temp.items():
            msgs.sort(key=lambda x: (x.creado_en, x.id), reverse=True)

        no_leidos: dict[int, int] = {}
        for aid, msgs in conversaciones_temp.items():
            no_leidos[aid] = sum(1 for x in msgs if not x.leido)

        ordenadas = sorted(
            conversaciones_temp.items(),
            key=lambda kv: kv[1][0].creado_en if kv[1] else timezone.now(),
            reverse=True,
        )
        conversaciones: OrderedDict[int, list[MensajeEmpleado]] = OrderedDict(ordenadas)

        nombres_admins: dict[int, str] = {}
        for aid in conversaciones.keys():
            u = Usuario.objects.filter(pk=aid).first()
            nombres_admins[aid] = self._nombre_usuario(u) or f"Administrador #{aid}"

        conversaciones_list: list[dict] = []
        for aid, msgs in conversaciones.items():
            nombre = nombres_admins.get(aid) or f"Administrador #{aid}"
            inicial = (nombre.strip()[:1] or "A").upper()
            conversaciones_list.append(
                {
                    "admin_id": aid,
                    "lista": msgs,
                    "nombre": nombre,
                    "inicial": inicial,
                    "no_leidos": no_leidos.get(aid, 0),
                }
            )

        mensajes_conversacion: list[dict] = []
        admin_conversacion: Usuario | None = None
        if conversacion_admin_id is not None:
            q_thread = Q(
                empleado_usuario_id=empleado_id,
                tipo_remitente=MensajeEmpleado.TipoRemitente.ADMIN,
                remitente_usuario_id=conversacion_admin_id,
            ) | Q(
                empleado_usuario_id=empleado_id,
                tipo_remitente=MensajeEmpleado.TipoRemitente.EMPLEADO,
                remitente_usuario_id=empleado_id,
            )
            thread = (
                MensajeEmpleado.objects.filter(q_thread)
                .select_related("remitente_usuario", "empleado_usuario")
                .order_by("-creado_en", "-id")
            )
            mensajes_conversacion = [self._mensaje_empleado_dto(m) for m in thread]
            admin_conversacion = Usuario.objects.filter(pk=conversacion_admin_id).first()

        return {
            "conversaciones_list": conversaciones_list,
            "conversacion_id": conversacion_admin_id,
            "mensajes_conversacion": mensajes_conversacion,
            "admin_conversacion": admin_conversacion,
        }

    def cliente_mensajes_ssr_context(
        self,
        *,
        usuario_id: int,
        conversacion_id: str | None,
    ) -> dict:
        items = self.listar_mensajes_directos(usuario_id) or []
        por_conv: dict[str, dict] = {}
        for m in items:
            cid = m.get("conversationId")
            if not cid:
                continue
            prev = por_conv.get(cid)
            if prev is None or (m.get("createdAt") or "") > (prev.get("createdAt") or ""):
                por_conv[cid] = m
        conversaciones = sorted(por_conv.values(), key=lambda x: x.get("createdAt") or "", reverse=True)
        mensajes_hilo: list[dict] = []
        if conversacion_id:
            mensajes_hilo = self.listar_mensajes_por_conversacion(conversacion_id) or []
        return {
            "md_conversaciones": conversaciones,
            "md_mensajes": mensajes_hilo,
            "conversation_id": conversacion_id,
        }
