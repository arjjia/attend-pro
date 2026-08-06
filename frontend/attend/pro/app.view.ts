namespace $.$$ {

	type TrustAnchor = {
		algorithm: 'ES256'
		key_id: string
		public_key_jwk: $attend_pro_crypto_jwk
	}

	type QrPayload = {
		version: 'attendpro.qr.v1'
		teacher_credential: $attend_pro_crypto_envelope
		permit: $attend_pro_crypto_envelope
		challenge: $attend_pro_crypto_envelope
	}

	export class $attend_pro_app extends $.$attend_pro_app {

		qr_rotation_timer: ReturnType< typeof setTimeout > | null = null
		qr_rotation_generation = 0
		sync_promise: Promise< void > | null = null

		@ $mol_mem
		store() {
			return new this.$.$attend_pro_store
		}

		@ $mol_mem
		giper() {
			return new this.$.$attend_pro_giper
		}

		api_base() {
			return location.port === '9080' ? 'http://localhost:8000/api/v1' : '/api/v1'
		}

		@ $mol_mem
		theme_dark( next?: boolean ) {
			if( next !== undefined ) {
				this.$.$mol_state_local.value( 'attendpro.theme.dark', next )
				return next
			}
			const stored = this.$.$mol_state_local.value( 'attendpro.theme.dark' )
			if( typeof stored === 'boolean' ) return stored
			return !this.$.$mol_lights()
		}

		theme_name() {
			return this.theme_dark() ? '$mol_theme_dark' : '$mol_theme_light'
		}

		theme_button_title() {
			return this.theme_dark() ? '☀ Светлая тема' : '☾ Тёмная тема'
		}

		theme_toggle( event?: Event ) {
			if( event === undefined ) return null
			this.theme_dark( !this.theme_dark() )
			return null
		}

		async api_async< Result >( path: string, init: RequestInit = {} ): Promise< Result > {
			const headers = new Headers( init.headers )
			if( init.body ) headers.set( 'Content-Type', 'application/json' )
			const response = await fetch( this.api_base() + path, {
				...init,
				headers,
				credentials: 'include',
			} )
			if( response.status === 204 ) return null as Result
			const body = await response.json().catch( () => null )
			if( !response.ok ) throw new Error( body?.detail ?? `HTTP ${ response.status }` )
			return body as Result
		}

		@ $mol_mem
		user( next?: $attend_pro_user | null ): $attend_pro_user | null {
			if( next !== undefined ) return next
			return $mol_wire_sync( this as $attend_pro_app ).user_load()
		}

		async user_load() {
			try {
				const user = await this.api_async< $attend_pro_user >( '/auth/me' )
				await this.store().put( 'Meta', 'active_user', user )
				return user
			} catch( error ) {
				if( !navigator.onLine ) return await this.store().get( 'Meta', 'active_user' ) as $attend_pro_user | undefined ?? null
				return null
			}
		}

		@ $mol_mem
		accounts(): $attend_pro_user[] {
			return $mol_wire_sync( this as $attend_pro_app ).api_async( '/auth/mock/accounts' ) as unknown as $attend_pro_user[]
		}

		@ $mol_mem
		device( next?: $attend_pro_device | null ): $attend_pro_device | null {
			if( next !== undefined ) return next
			const user = this.user()
			if( !user ) return null
			return $mol_wire_sync( this as $attend_pro_app ).device_init( user )
		}

		async device_init( user: $attend_pro_user ) {
			const stored = await this.store().get( 'Devices', user.id )
			if( stored && Date.parse( String( stored.credential.payload.expires_at ) ) > Date.now() ) return stored
			if( !navigator.onLine ) throw new Error( 'Это устройство ещё не зарегистрировано. Один раз подключитесь к порталу.' )
			const pair = await this.$.$attend_pro_crypto_key_pair()
			const device_id = crypto.randomUUID()
			const credential = await this.api_async< $attend_pro_crypto_envelope >( '/devices/enroll', {
				method: 'POST',
				body: JSON.stringify({
					device_id,
					label: `${ navigator.platform || 'Browser' } / ${ new Date().toLocaleDateString( 'ru-RU' ) }`,
					public_key_jwk: pair.public_jwk,
				}),
			} )
			const device: $attend_pro_device = {
				user_id: user.id,
				device_id,
				private_key: pair.private_key,
				public_jwk: pair.public_jwk,
				credential,
			}
			await this.store().put( 'Devices', user.id, device )
			return device
		}

		@ $mol_mem
		current( next?: $attend_pro_lesson | null ): $attend_pro_lesson | null {
			if( next !== undefined ) return next
			const user = this.user()
			if( !user ) return null
			return $mol_wire_sync( this as $attend_pro_app ).current_load()
		}

		async current_load() {
			try {
				const lesson = await this.api_async< $attend_pro_lesson | null >( '/schedule/current' )
				if( lesson ) await this.store().put( 'Meta', 'current_lesson', lesson )
				return lesson
			} catch( error ) {
				const cached = await this.store().get( 'Meta', 'current_lesson' ) as $attend_pro_lesson | undefined
				return cached ?? null
			}
		}

		@ $mol_mem
		trust( next?: TrustAnchor | null ): TrustAnchor | null {
			if( next !== undefined ) return next
			return $mol_wire_sync( this as $attend_pro_app ).trust_load()
		}

		async trust_load() {
			try {
				const trust = await this.api_async< TrustAnchor >( '/system/trust' )
				await this.store().put( 'Meta', 'trust_anchor', trust )
				return trust
			} catch( error ) {
				return await this.store().get( 'Meta', 'trust_anchor' ) as TrustAnchor | undefined ?? null
			}
		}

		@ $mol_mem
		permit( next?: $attend_pro_permit_bundle | null ): $attend_pro_permit_bundle | null {
			if( next !== undefined ) return next
			// Loading an async value from this reactive getter leaked $mol's suspense
			// object into the UI as "[object ...permit_load...]". Permits are now loaded
			// explicitly by the async login/QR flows and cached through this setter.
			return null
		}

		async permit_load( lesson: $attend_pro_lesson, device: $attend_pro_device, force = false ) {
			const cached = await this.store().get( 'Permits', lesson.id )
			if( !force && cached && Date.parse( String( cached.permit.payload.expires_at ) ) > Date.now() ) return cached
			if( !navigator.onLine ) {
				if( cached ) return cached
				throw new Error( 'Нет заранее загруженного разрешения пары: преподавателю нужно один раз подключиться к порталу.' )
			}
			const bundle = await this.api_async< $attend_pro_permit_bundle >( `/lessons/${ lesson.id }/permit`, {
				method: 'POST',
				body: JSON.stringify({ device_credential_id: device.credential.payload.credential_id }),
			} )
			await this.store().put( 'Permits', lesson.id, bundle )
			return bundle
		}

		app_tools() {
			return this.user()
				? [ this.Network(), this.Theme_toggle(), this.Logout() ]
				: [ this.Network(), this.Theme_toggle() ]
		}

		rows() {
			try {
				const user = this.user()
				const base: $mol_view[] = [ this.Intro() ]
				if( this.error_text() ) base.push( this.Error() )
				if( !user ) return [ ...base, this.Accounts_title(), ...this.accounts().map( account => this.Account( account.id ) ) ]
				this.device()
				base.push( this.Identity() )
				base.push( this.current() ? this.Lesson() : this.No_lesson() )
				return user.role === 'teacher' ? [ ...base, ...this.teacher_rows() ] : [ ...base, ...this.student_rows() ]
			} catch( error: any ) {
				if( this.$.$mol_promise_like( error ) ) throw error
				this.error_text( error?.message ?? String( error ) )
				return [ this.Intro(), this.Error() ]
			}
		}

		teacher_rows() {
			const rows: $mol_view[] = [ this.Teacher_explain(), this.Test_lesson_explain(), this.Start_now() ]
			if( this.action_status() ) rows.push( this.Action_status() )
			if( this.current() ) rows.push( this.Qr_kind_explain(), this.Qr_actions() )
			if( this.qr_uri() ) rows.push( this.Stop_qr(), this.Qr(), this.Qr_hint(), this.Qr_raw() )
			return rows
		}

		student_rows() {
			const rows: $mol_view[] = [ this.Student_explain() ]
			if( this.scan_active() ) rows.push( this.Camera() )
			rows.push( this.Start_scan(), this.Qr_input(), this.Accept_qr(), this.Scan_status(), this.Pending() )
			if( this.pending_count() ) rows.push( this.Sync() )
			rows.push( this.History() )
			return rows
		}

		network_label() {
			this.$.$mol_state_time.now( 1000 )
			return navigator.onLine ? '● сеть доступна' : '○ офлайн-режим'
		}

		account_title( id: string ) {
			const account = this.accounts().find( ( item: $attend_pro_user ) => item.id === id )!
			return `${ account.role === 'teacher' ? 'Преподаватель' : 'Студент' }: ${ account.full_name }`
		}

		account_login( id: string, event?: Event ) {
			if( event === undefined ) return null
			void this.account_login_async( id ).catch( error => {
				this.error_text( error?.message ?? String( error ) )
			} )
			return null
		}

		async account_login_async( id: string ) {
			const account = this.accounts().find( ( item: $attend_pro_user ) => item.id === id )!
			const user = await this.login_async( account.email )
			// The mock endpoint sets an HttpOnly cookie. Let the browser commit it before
			// starting authenticated requests; real SSO will naturally have a redirect.
			await new Promise( done => setTimeout( done, 100 ) )
			const device = await this.device_init( user )
			const [ lesson, trust ] = await Promise.all([
				this.current_load(),
				this.trust_load(),
			])
			let permit: $attend_pro_permit_bundle | null = null
			if( user.role === 'teacher' && lesson ) {
				permit = await this.permit_load( lesson, device )
			}
			this.device( device )
			this.current( lesson )
			this.permit( permit )
			this.trust( trust )
			this.user( user )
			this.error_text( '' )
		}

		async login_async( email: string ) {
			const user = await this.api_async< $attend_pro_user >( '/auth/mock/login', {
				method: 'POST', body: JSON.stringify({ email }),
			} )
			await this.store().put( 'Meta', 'active_user', user )
			return user
		}

		logout( event?: Event ) {
			if( event === undefined ) return null
			void this.logout_flow_async().catch( error => {
				this.error_text( error?.message ?? String( error ) )
			} )
			return null
		}

		async logout_flow_async() {
			this.qr_rotation_stop()
			await this.logout_async()
			this.user( null )
			this.device( null )
			this.current( null )
			this.permit( null )
		}

		async logout_async() {
			await this.api_async( '/auth/logout', { method: 'POST' } )
			await this.store().drop( 'Meta', 'active_user' )
		}

		identity_name() {
			return this.user()?.full_name ?? ''
		}

		identity_role() {
			const user = this.user()
			if( !user ) return ''
			return user.role === 'teacher' ? 'Преподаватель · устройство имеет собственный ключ' : `Студент · ${ user.group_name } · устройство имеет собственный ключ`
		}

		lesson_state() {
			return this.current()?.state === 'current' ? 'Пара идёт сейчас' : 'Сохранено для офлайн-работы'
		}

		lesson_title() {
			const lesson = this.current()
			return lesson ? `${ lesson.course_code } · ${ lesson.title }` : ''
		}

		lesson_meta() {
			const lesson = this.current()
			if( !lesson ) return ''
			const start = new Date( lesson.starts_at ).toLocaleTimeString( 'ru-RU', { hour: '2-digit', minute: '2-digit' } )
			const end = new Date( lesson.ends_at ).toLocaleTimeString( 'ru-RU', { hour: '2-digit', minute: '2-digit' } )
			return `${ lesson.kind } · ${ lesson.group_name } · ${ lesson.room } · ${ start }–${ end }`
		}

		start_now_title() {
			return this.current()?.state === 'current'
				? 'Перезапустить тестовую пару на 90 минут'
				: 'Запустить тестовую пару на 90 минут'
		}

		start_now( event?: Event ) {
			if( event === undefined ) return null
			this.action_status( 'Перезапускаю тестовую пару и получаю новое подписанное разрешение…' )
			void this.start_now_flow_async().catch( error => {
				const message = error?.message ?? String( error )
				this.action_status( `Не удалось перезапустить пару: ${ message }` )
				this.error_text( message )
			} )
			return null
		}

		async start_now_flow_async() {
			this.qr_rotation_stop()
			const lesson = await this.start_now_async()
			this.current( lesson )
			const device = this.device()!
			const permit = await this.permit_load( lesson, device, true )
			this.permit( permit )
			this.action_status( 'Тестовая пара перезапущена на 90 минут. Старый QR остановлен, новое разрешение сохранено в IndexedDB.' )
			this.error_text( '' )
		}

		async start_now_async() {
			const lesson = await this.api_async< $attend_pro_lesson >( '/test/lessons/start-now', {
				method: 'POST', body: JSON.stringify({ duration_minutes: 90 }),
			} )
			await this.store().put( 'Meta', 'current_lesson', lesson )
			await this.store().drop( 'Permits', lesson.id )
			return lesson
		}

		entry_qr( event?: Event ) {
			if( event === undefined ) return null
			void this.qr_rotation_start_async( 'ENTRY' ).catch( error => {
				this.error_text( error?.message ?? String( error ) )
			} )
			return null
		}

		exit_qr( event?: Event ) {
			if( event === undefined ) return null
			void this.qr_rotation_start_async( 'EXIT' ).catch( error => {
				this.error_text( error?.message ?? String( error ) )
			} )
			return null
		}

		@ $mol_mem
		active_qr_kind( next?: 'ENTRY' | 'EXIT' | null ): 'ENTRY' | 'EXIT' | null {
			if( next !== undefined ) return next
			return null
		}

		@ $mol_mem
		qr_rotates_at( next?: number ) {
			if( next !== undefined ) return next
			return 0
		}

		entry_qr_title() {
			return this.active_qr_kind() === 'ENTRY' ? 'Обновить QR «Вход» сейчас' : 'Показывать QR «Вход»'
		}

		exit_qr_title() {
			return this.active_qr_kind() === 'EXIT' ? 'Обновить QR «Выход» сейчас' : 'Показывать QR «Выход»'
		}

		stop_qr( event?: Event ) {
			if( event === undefined ) return null
			this.qr_rotation_stop()
			this.action_status( 'Автоматический показ QR остановлен.' )
			return null
		}

		qr_rotation_stop() {
			if( this.qr_rotation_timer !== null ) clearTimeout( this.qr_rotation_timer )
			this.qr_rotation_timer = null
			this.qr_rotation_generation++
			this.active_qr_kind( null )
			this.qr_rotates_at( 0 )
			this.qr_uri( '' )
			this.qr_raw( '' )
		}

		async qr_rotation_start_async( kind: 'ENTRY' | 'EXIT' ) {
			if( this.qr_rotation_timer !== null ) clearTimeout( this.qr_rotation_timer )
			this.qr_rotation_timer = null
			const generation = ++this.qr_rotation_generation
			this.active_qr_kind( kind )
			this.error_text( '' )
			await this.make_qr_async( kind, generation )
			this.qr_rotation_schedule( kind, generation )
		}

		qr_rotation_schedule( kind: 'ENTRY' | 'EXIT', generation: number ) {
			if( generation !== this.qr_rotation_generation ) return
			// Each challenge is valid for 30 seconds. Rotating at 25 seconds leaves a
			// five-second overlap for a camera that started reading the previous frame.
			const delay = 25_000
			this.qr_rotates_at( Date.now() + delay )
			this.qr_rotation_timer = setTimeout( () => {
				if( generation !== this.qr_rotation_generation ) return
				void this.make_qr_async( kind, generation ).then( () => {
					this.qr_rotation_schedule( kind, generation )
				} ).catch( error => {
					this.qr_rotation_stop()
					this.error_text( `Автообновление QR остановлено: ${ error?.message ?? String( error ) }` )
				} )
			}, delay )
		}

		qr_hint() {
			const kind = this.active_qr_kind()
			if( !kind ) return ''
			const now = this.$.$mol_state_time.now( 1000 )
			const seconds = Math.max( 0, Math.ceil( ( this.qr_rotates_at() - now ) / 1000 ) )
			return `${ kind === 'ENTRY' ? 'ВХОД' : 'ВЫХОД' }: каждый QR действует 30 секунд и автоматически заменяется новым через ${ seconds } с. Обновление подписывается локально${ navigator.onLine ? '' : ' и работает офлайн' }.`
		}

		async make_qr_async( kind: 'ENTRY' | 'EXIT', generation = this.qr_rotation_generation ) {
			const lesson = this.current()
			const device = this.device()
			let bundle = this.permit()
			if( !lesson || !device ) throw new Error( 'Нет активной пары или ключа преподавателя' )
			if( !bundle ) {
				bundle = await this.permit_load( lesson, device )
				this.permit( bundle )
			}
			const issued = new Date()
			const challenge_payload = {
				version: 'attendpro.teacher-challenge.v1',
				challenge_id: crypto.randomUUID(),
				lesson_id: lesson.id,
				permit_id: bundle.permit.payload.permit_id,
				teacher_device_id: device.device_id,
				kind,
				nonce: this.$.$attend_pro_crypto_b64url( crypto.getRandomValues( new Uint8Array( 32 ) ) ),
				issued_at: issued.toISOString(),
				expires_at: new Date( issued.getTime() + 30_000 ).toISOString(),
			}
			const challenge: $attend_pro_crypto_envelope = {
				payload: challenge_payload,
				signature: await this.$.$attend_pro_crypto_sign( device.private_key, challenge_payload ),
				key_id: device.device_id,
				algorithm: 'ES256',
			}
			const qr: QrPayload = {
				version: 'attendpro.qr.v1',
				teacher_credential: bundle.teacher_credential,
				permit: bundle.permit,
				challenge,
			}
			const raw = JSON.stringify( qr )
			const qrcode = require( 'qrcode/lib/browser.js' ) as typeof import( 'qrcode' )
			// A single byte segment is also more compact for the JSON protocol and
			// avoids the text-mode segmentation optimiser that is useless here.
			const uri = await ( qrcode.toDataURL as any )(
				[{ data: raw, mode: 'byte' }],
				{ errorCorrectionLevel: 'L', width: 760, margin: 2 },
			)
			if( generation !== this.qr_rotation_generation || this.active_qr_kind() !== kind ) return
			this.qr_raw( raw )
			this.qr_uri( uri )
		}

		@ $mol_mem
		scan_active( next?: boolean ) {
			return next ?? false
		}

		scan_button_title() {
			return this.scan_active() ? 'Остановить камеру' : 'Включить камеру и искать QR'
		}

		scan_start( event?: Event ) {
			if( event === undefined ) return null
			const active = !this.scan_active()
			this.scan_active( active )
			this.scan_status( active ? 'Камера включена: наведите её на QR преподавателя.' : 'Сканирование остановлено.' )
			if( active ) new $mol_after_timeout( 300, () => this.scan_once() )
			return null
		}

		scan_once() {
			if( !this.scan_active() ) return
			try {
				const video = this.Camera().dom_node() as HTMLVideoElement
				if( video.videoWidth && video.videoHeight ) {
					const canvas = document.createElement( 'canvas' )
					canvas.width = video.videoWidth
					canvas.height = video.videoHeight
					const context = canvas.getContext( '2d', { willReadFrequently: true } )!
					context.drawImage( video, 0, 0 )
					const image = context.getImageData( 0, 0, canvas.width, canvas.height )
					const module = require( 'jsqr/dist/jsQR.js' ) as typeof import( 'jsqr' )
					const jsqr = ( module as any ).default ?? module
					const result = jsqr( image.data, image.width, image.height, { inversionAttempts: 'attemptBoth' } )
					if( result?.data ) {
						this.scan_active( false )
						this.qr_input( result.data )
						this.claim_submit( result.data )
						return
					}
				}
			} catch( error: any ) {
				this.scan_status( `Камера пока не готова: ${ error.message }` )
			}
			new $mol_after_timeout( 250, () => this.scan_once() )
		}

		qr_accept( event?: Event ) {
			if( event === undefined ) return null
			this.claim_submit( this.qr_input() )
			return null
		}

		@ $mol_mem
		claim_busy( next?: boolean ) {
			if( next !== undefined ) return next
			return false
		}

		accept_qr_enabled() {
			return !this.claim_busy()
		}

		accept_qr_title() {
			return this.claim_busy() ? 'Проверяю подписи и сохраняю…' : 'Проверить и подписать вставленный QR'
		}

		claim_submit( raw: string ) {
			if( this.claim_busy() ) return
			this.claim_busy( true )
			this.scan_status( 'Проверяю всю цепочку подписей и сохраняю отметку на устройстве…' )
			void this.accept_qr_async( raw ).catch( error => {
				this.scan_status( `QR отклонён: ${ error?.message ?? String( error ) }` )
			} ).finally( () => {
				this.claim_busy( false )
			} )
		}

		async verified_portal_envelope( envelope: $attend_pro_crypto_envelope, trust: TrustAnchor ) {
			if( envelope.algorithm !== 'ES256' || envelope.key_id !== trust.key_id ) return false
			return await this.$.$attend_pro_crypto_verify( trust.public_key_jwk, envelope.payload, envelope.signature )
		}

		async accept_qr_async( raw: string ) {
			const user = this.user()
			const device = this.device()
			const trust = await this.trust_load()
			if( !user || user.role !== 'student' || !device ) throw new Error( 'Нужен вход студента и ключ устройства' )
			if( !trust ) throw new Error( 'На устройстве ещё нет открытого ключа портала' )
			let qr: QrPayload
			try {
				qr = JSON.parse( raw )
			} catch( _error ) {
				throw new Error( 'QR не содержит корректный JSON AttendPro' )
			}
			if( qr.version !== 'attendpro.qr.v1' ) throw new Error( 'Неизвестная версия QR' )
			if( !await this.verified_portal_envelope( qr.teacher_credential, trust ) ) throw new Error( 'Недействительна подпись сертификата преподавателя' )
			if( !await this.verified_portal_envelope( qr.permit, trust ) ) throw new Error( 'Недействительна подпись разрешения пары' )
			const challenge = qr.challenge.payload
			const captured_at = new Date()
			const captured_ms = captured_at.getTime()
			const skew_ms = 120_000
			if( challenge.version !== 'attendpro.teacher-challenge.v1' ) throw new Error( 'Неизвестная версия вызова' )
			if( qr.challenge.algorithm !== 'ES256' ) throw new Error( 'Неподдерживаемый алгоритм подписи QR' )
			if( qr.teacher_credential.payload.role !== 'teacher' ) throw new Error( 'QR выпущен не преподавателем' )
			if( challenge.permit_id !== qr.permit.payload.permit_id ) throw new Error( 'QR не связан с разрешением пары' )
			if( challenge.teacher_device_id !== qr.teacher_credential.payload.device_id ) throw new Error( 'QR подписан другим устройством' )
			if( qr.challenge.key_id !== challenge.teacher_device_id ) throw new Error( 'Идентификатор ключа QR не совпадает с устройством' )
			if( challenge.lesson_id !== qr.permit.payload.lesson_id ) throw new Error( 'QR относится к другой паре' )
			if( qr.permit.payload.teacher_user_id !== qr.teacher_credential.payload.user_id ) throw new Error( 'Разрешение выдано другому преподавателю' )
			if( qr.permit.payload.teacher_device_credential_id !== qr.teacher_credential.payload.credential_id ) throw new Error( 'Разрешение выдано другому устройству' )
			if( !Array.isArray( qr.permit.payload.allowed_kinds ) || !qr.permit.payload.allowed_kinds.includes( challenge.kind ) ) throw new Error( 'Разрешение не допускает этот тип отметки' )
			if( challenge.kind !== 'ENTRY' && challenge.kind !== 'EXIT' ) throw new Error( 'Неизвестный тип отметки' )
			const issued_ms = Date.parse( challenge.issued_at )
			const expires_ms = Date.parse( challenge.expires_at )
			const permit_from_ms = Date.parse( qr.permit.payload.not_before )
			const permit_to_ms = Date.parse( qr.permit.payload.expires_at )
			const credential_from_ms = Date.parse( qr.teacher_credential.payload.issued_at )
			const credential_to_ms = Date.parse( qr.teacher_credential.payload.expires_at )
			if( ![ issued_ms, expires_ms, permit_from_ms, permit_to_ms, credential_from_ms, credential_to_ms ].every( Number.isFinite ) ) throw new Error( 'В QR есть некорректная временная метка' )
			if( expires_ms <= issued_ms || expires_ms - issued_ms > 30_000 ) throw new Error( 'Некорректный срок жизни QR' )
			if( captured_ms < issued_ms - skew_ms ) throw new Error( 'Часы преподавателя слишком далеко впереди' )
			if( captured_ms > expires_ms + skew_ms ) throw new Error( 'QR уже истёк' )
			if( captured_ms < permit_from_ms - skew_ms || captured_ms > permit_to_ms + skew_ms ) throw new Error( 'Разрешение пары сейчас не действует' )
			if( captured_ms < credential_from_ms - skew_ms || captured_ms > credential_to_ms + skew_ms ) throw new Error( 'Сертификат устройства преподавателя сейчас не действует' )
			if( !await this.$.$attend_pro_crypto_verify(
				qr.teacher_credential.payload.public_key_jwk,
				challenge,
				qr.challenge.signature,
			) ) throw new Error( 'Подпись преподавателя под QR неверна' )
			const claim_payload = {
				version: 'attendpro.student-claim.v1',
				claim_id: crypto.randomUUID(),
				challenge_id: challenge.challenge_id,
				challenge_digest: await this.$.$attend_pro_crypto_digest( qr.challenge ),
				lesson_id: challenge.lesson_id,
				kind: challenge.kind,
				student_user_id: user.id,
				student_device_id: device.device_id,
				captured_at: captured_at.toISOString(),
			}
			const claim: $attend_pro_crypto_envelope = {
				payload: claim_payload,
				signature: await this.$.$attend_pro_crypto_sign( device.private_key, claim_payload ),
				key_id: device.device_id,
				algorithm: 'ES256',
			}
			const proof: $attend_pro_proof = {
				teacher_credential: qr.teacher_credential,
				permit: qr.permit,
				challenge: qr.challenge,
				student_credential: device.credential,
				claim,
				replica_refs: [],
			}
			await this.store().put( 'Pending', claim_payload.claim_id, proof )
			this.pending_count( ( await this.store().pending_entries() ).length )
			this.scan_status( `Подписи проверены. Отметка ${ challenge.kind } сохранена локально${ navigator.onLine ? ' и готова к отправке' : '; отправится после появления сети' }.` )
			// Portal synchronization is deliberately outside the capture transaction.
			// The student receives a responsive, durable local result first; network
			// delivery starts when the UI is idle.
			this.claim_followup_schedule( claim_payload.claim_id )
		}

		claim_followup_schedule( claim_id: string ) {
			new this.$.$mol_after_work( 1500, () => {
				void this.claim_followup_async( claim_id ).catch( error => {
					this.$.$mol_log3_warn({
						place: this,
						message: 'Deferred claim synchronization failed',
						hint: error?.message ?? String( error ),
					})
				} )
			} )
		}

		async claim_followup_async( claim_id: string ) {
			if( !await this.store().get( 'Pending', claim_id ) ) return
			// Do not execute Giper Land signing on the browser main thread. On mobile
			// devices its synchronous cryptographic pipeline can block rendering for
			// tens of seconds. The proof remains self-contained in IndexedDB and on the
			// portal; Giper publication will be re-enabled from a dedicated Web Worker.
			if( navigator.onLine ) await this.sync_async()
		}

		@ $mol_mem
		pending_count( next?: number ): number {
			if( next !== undefined ) return next
			return $mol_wire_sync( this as $attend_pro_app ).pending_count_load()
		}

		async pending_count_load() {
			return ( await this.store().pending_entries() ).length
		}

		pending_label() {
			const count = this.pending_count()
			return count ? `В IndexedDB ожидают синхронизации: ${ count }.` : 'Локальная очередь синхронизации пуста.'
		}

		sync_enabled() {
			return navigator.onLine && this.pending_count() > 0
		}

		sync_now( event?: Event ) {
			if( event === undefined ) return null
			void this.sync_async().catch( error => {
				this.scan_status( `Синхронизация не выполнена: ${ error?.message ?? String( error ) }` )
			} )
			return null
		}

		async sync_async() {
			if( this.sync_promise ) return await this.sync_promise
			const running = this.sync_run_async()
			this.sync_promise = running
			try {
				await running
			} finally {
				if( this.sync_promise === running ) this.sync_promise = null
			}
		}

		async sync_run_async() {
			const pending = await this.store().pending_entries()
			if( !pending.length ) return
			const trust = await this.trust_load()
			if( !trust ) throw new Error( 'Нет доверенного открытого ключа портала для проверки решения' )
			let accepted = 0
			let processed = 0
			for( let offset = 0; offset < pending.length; offset += 100 ) {
				const batch = pending.slice( offset, offset + 100 ).map( item => ({
					...item,
					proof: { ...item.proof, replica_refs: item.proof.replica_refs ?? [] },
				}) )
				const response = await this.api_async< { results: Array<{ claim_id: string, decision: $attend_pro_crypto_envelope }> } >( '/claims/sync', {
					method: 'POST',
					body: JSON.stringify({ claims: batch.map( item => item.proof ) }),
				} )
				if( response.results.length !== batch.length ) throw new Error( 'Портал вернул неполный набор решений' )
				for( let index = 0; index < response.results.length; index++ ) {
					const result = response.results[ index ]
					const source = batch[ index ]
					const decision = result.decision
					if( result.claim_id !== source.claim_id || decision.payload.claim_id !== source.claim_id ) throw new Error( 'Решение портала относится к другой отметке' )
					if( decision.payload.version !== 'attendpro.portal-decision.v1' ) throw new Error( 'Портал вернул неизвестную версию решения' )
					if( decision.payload.evidence_hash !== await this.$.$attend_pro_crypto_digest( source.proof ) ) throw new Error( 'Решение портала не связано с отправленным доказательством' )
					if( !await this.verified_portal_envelope( decision, trust ) ) throw new Error( 'Подпись решения портала недействительна' )
					await this.store().put( 'Decisions', result.claim_id, decision )
					await this.store().drop( 'Pending', result.claim_id )
					if( decision.payload.status === 'ACCEPTED' ) accepted++
					processed++
				}
				this.pending_count( Math.max( 0, pending.length - processed ) )
			}
			this.history_count( this.history_count() + accepted )
			this.scan_status( `Синхронизация завершена: портал подтвердил ${ accepted } из ${ processed } отметок.` )
		}

		@ $mol_mem
		history_count( next?: number ): number {
			if( next !== undefined ) return next
			return $mol_wire_sync( this as $attend_pro_app ).history_count_load()
		}

		async history_count_load() {
			const local = () => this.store().all( 'Decisions' ).then( decisions =>
				decisions.filter( decision => decision.payload.status === 'ACCEPTED' ).length
			)
			if( !navigator.onLine ) return await local()
			try {
				return ( await this.api_async< any[] >( '/attendance/me' ) ).length
			} catch( _error ) {
				return await local()
			}
		}

		history_label() {
			return `Подтверждённых порталом отметок: ${ this.history_count() }. Подписанные решения также сохранены на устройстве.`
		}

	}

}

namespace $ {
	$mol_offline()
}
