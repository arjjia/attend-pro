export function LoadingState({ label = "Загружаем данные" }: { label?: string }) {
  return <div className="loading-state" role="status"><span className="spinner" />{label}</div>;
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="error-state" role="alert">
      <b>Что-то пошло не так</b>
      <span>{message}</span>
      {retry && <button type="button" className="secondary-button" onClick={retry}>Повторить</button>}
    </div>
  );
}
