import { existsSync } from 'node:fs'
import { cp, mkdir, rm, symlink } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'


const frontend = path.resolve( path.dirname( fileURLToPath( import.meta.url ) ), '..' )
const workspace = path.join( frontend, '.mam' )
const binary = path.join( frontend, 'node_modules', 'mam', 'mol', 'build', 'bin' )

function run( command, args, cwd ) {
	return new Promise( ( resolve, reject ) => {
		const child = spawn( command, args, { cwd, stdio: 'inherit' } )
		child.once( 'error', reject )
		child.once( 'exit', code => code === 0 ? resolve() : reject( new Error( `${ command } exited with ${ code }` ) ) )
	} )
}

async function prepare() {
	await mkdir( workspace, { recursive: true } )
	if( !existsSync( path.join( workspace, '.git' ) ) ) {
		await rm( workspace, { recursive: true, force: true } )
		await run( 'git', [ 'clone', '--depth', '1', 'https://github.com/hyoo-ru/mam.git', workspace ], frontend )
	}
	const source_link = path.join( workspace, 'attend' )
	await rm( source_link, { recursive: true, force: true } )
	await symlink( path.join( '..', 'attend' ), source_link, 'dir' )
	const modules_link = path.join( workspace, 'node_modules' )
	if( !existsSync( modules_link ) ) await symlink( path.join( '..', 'node_modules' ), modules_link, 'dir' )
}

await prepare()
const mode = process.argv[ 2 ] ?? 'build'
if( mode === 'dev' ) {
	await run( process.execPath, [ binary ], workspace )
} else {
	await run( process.execPath, [ binary, 'attend/pro' ], workspace )
	const output = path.join( frontend, 'attend', 'pro', '-' )
	const dist = path.join( frontend, 'dist' )
	await rm( dist, { recursive: true, force: true } )
	await cp( output, dist, { recursive: true } )
}
