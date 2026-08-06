// Giper Baza already uses the 2025 DataView Float16 API. Keep the MVP buildable
// and functional on runtimes whose TypeScript lib or browser is one revision behind.
interface DataView< TArrayBuffer extends ArrayBufferLike = ArrayBufferLike > {
	getFloat16( byteOffset: number, littleEndian?: boolean ): number
	setFloat16( byteOffset: number, value: number, littleEndian?: boolean ): void
}

declare var Float16Array: {
	new( buffer: ArrayBuffer, byteOffset?: number, length?: number ): Float16Array< ArrayBuffer >
	readonly BYTES_PER_ELEMENT: number
}

const $attend_pro_giper_data_view = DataView.prototype as any

if( typeof $attend_pro_giper_data_view.getFloat16 !== 'function' ) {
	$attend_pro_giper_data_view.getFloat16 = function( this: DataView, byteOffset: number, littleEndian = false ) {
		const bits = this.getUint16( byteOffset, littleEndian )
		const sign = bits >> 15 ? -1 : 1
		const exponent = ( bits >> 10 ) & 0x1f
		const fraction = bits & 0x3ff
		if( exponent === 0 ) return sign * 2 ** -14 * ( fraction / 1024 )
		if( exponent === 0x1f ) return fraction ? Number.NaN : sign * Number.POSITIVE_INFINITY
		return sign * 2 ** ( exponent - 15 ) * ( 1 + fraction / 1024 )
	}
}

if( typeof $attend_pro_giper_data_view.setFloat16 !== 'function' ) {
	$attend_pro_giper_data_view.setFloat16 = function( this: DataView, byteOffset: number, value: number, littleEndian = false ) {
		const sign = value < 0 || Object.is( value, -0 ) ? 0x8000 : 0
		const absolute = Math.abs( value )
		let bits: number
		if( Number.isNaN( absolute ) ) bits = sign | 0x7e00
		else if( absolute === Number.POSITIVE_INFINITY ) bits = sign | 0x7c00
		else if( absolute === 0 ) bits = sign
		else {
			const exponent = Math.floor( Math.log2( absolute ) )
			if( exponent < -14 ) bits = sign | Math.round( absolute / 2 ** -24 )
			else if( exponent > 15 ) bits = sign | 0x7c00
			else bits = sign | ( exponent + 15 ) << 10 | Math.round( ( absolute / 2 ** exponent - 1 ) * 1024 )
		}
		this.setUint16( byteOffset, bits & 0xffff, littleEndian )
	}
}
